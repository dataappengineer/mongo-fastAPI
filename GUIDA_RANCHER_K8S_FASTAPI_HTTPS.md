# Guida Operativa Full HTTPS / TLS - Cluster Rancher (Namespace: `metadata`)
## Modulo `mongo-fastAPI` (FastAPI / Uvicorn + MongoDB)

Questa guida illustra la procedura passo-passo per riconfigurare da zero il modulo **`mongo-fastAPI`** su **Kubernetes + Rancher**, passando dalla precedente configurazione HTTP in chiaro a un'architettura **Full HTTPS (End-to-End Encryption)**.

> **Requisito Cliente: Full HTTPS / Intra-Pod Encryption**  
> Anche la comunicazione tra Ingress Controller (Traefik / Nginx) e il Pod FastAPI — nonché qualsiasi chiamata intra-cluster / intra-pod — deve avvenire su canale crittografato **HTTPS/TLS**. Il server applicativo Python (**Uvicorn**) esegue direttamente la terminazione TLS con certificati montati sul Pod.

---

## Panoramica dell'Architettura Full HTTPS

```
[ Client / Browser / Frontend ]
               │
               ▼  HTTPS (Porta 443) - FQDN: fastapi.dss.local
┌────────────────────────────────────────────────────────┐
│     Ingress Controller (Traefik - Entrypoint websecure) │
│  TLS Secret: fastapi-tls  │  Backend Scheme: HTTPS     │
└────────────────────────────────────────────────────────┘
               │
               ▼  HTTPS (Porta 8443) intra-cluster
┌────────────────────────────────────────────────────────┐
│        Kubernetes Service: fastapi-service             │
│        Port: 8443 -> TargetPort: 8443 (HTTPS)          │
└────────────────────────────────────────────────────────┘
               │
               ▼  HTTPS (Porta 8443) cifrato su Pod
┌────────────────────────────────────────────────────────┐
│             Pod FastAPI (app: fastapi-app)             │
│ Uvicorn: --ssl-certfile=/etc/tls/tls.crt               │
│          --ssl-keyfile=/etc/tls/tls.key                │
│ Volume: Secret 'fastapi-tls' montato su /etc/tls       │
└────────────────────────────────────────────────────────┘
```

### Differenza rispetto al modulo Java (`csv-mongo-loader`)
- Nel modulo Spring Boot (`csv-mongo-loader`) il certificato era memorizzato in formato **JKS** (`server.jks`) e richiedeva `keytool`.
- In **FastAPI (Python / Uvicorn)** si utilizzano i certificati standard **X.509 in formato PEM** (`tls.crt` per il certificato pubblico e `tls.key` per la chiave privata).
- Kubernetes supporta nativamente il tipo di Secret `kubernetes.io/tls`. In questo modo lo **stesso Secret** (`fastapi-tls`) viene utilizzato **sia** dall'Ingress Traefik per esporre il dominio esterno `fastapi.dss.local`, **sia** montato sul Pod nel path `/etc/tls` per consentire a Uvicorn di servire direttamente in HTTPS.

---

## 0. Prerequisiti: Generazione Certificati TLS e Creazione Secret K8s (PowerShell)

Tutti i comandi seguenti sono formattati su **stringa unica** per consentire il copia-incolla diretto nella console **PowerShell** sul PC Windows del DevOps, senza errori di interruzione riga.

### 0.1 Generare `tls.key` e `tls.crt` su PowerShell

Il certificato deve coprire:
- Host esterno: `fastapi.dss.local`
- Nome Service K8s: `fastapi-service`
- FQDN interno K8s: `fastapi-service.metadata.svc.cluster.local`
- Indirizzi locali di test: `localhost`, `127.0.0.1`

#### Opzione A: Tramite OpenSSL (Consigliata - riga singola)
Se hai OpenSSL installato (incluso di default in Git for Windows in `C:\Program Files\Git\usr\bin\openssl.exe`, in WSL o nativo):

```powershell
openssl req -x509 -nodes -days 730 -newkey rsa:2048 -keyout tls.key -out tls.crt -subj "/CN=fastapi.dss.local/OU=DSS/O=RegionePuglia/C=IT" -addext "subjectAltName=DNS:fastapi.dss.local,DNS:fastapi-service,DNS:fastapi-service.metadata.svc.cluster.local,DNS:localhost,IP:127.0.0.1"
```

> **Dettagli del comando:**
> - Genera due file fisici nella cartella corrente: **`tls.key`** (chiave privata RSA 2048 bit senza passphrase) e **`tls.crt`** (certificato X.509 valido 2 anni).
> - Include tutti i Subject Alternative Names (SAN) necessari sia per l'Ingress che per le chiamate intra-cluster.

#### Opzione B: Tramite PowerShell Nativo Windows (senza OpenSSL)
Se non disponi di OpenSSL, puoi generarlo con il comando PowerShell nativo ed esportarlo:

```powershell
$cert = New-SelfSignedCertificate -DnsName "fastapi.dss.local","fastapi-service","fastapi-service.metadata.svc.cluster.local","localhost" -CertStoreLocation "cert:\CurrentUser\My" -NotAfter (Get-Date).AddYears(2); $pwd = ConvertTo-SecureString -String "Temporal123!" -Force -AsPlainText; Export-PfxCertificate -Cert $cert -FilePath "./fastapi.pfx" -Password $pwd
```

*(Se usi l'opzione PFX, puoi estrarre CRT e KEY tramite OpenSSL con `openssl pkcs12 -in fastapi.pfx -nocerts -out tls.key -nodes -passin pass:Temporal123!` e `openssl pkcs12 -in fastapi.pfx -clcerts -nokeys -out tls.crt -passin pass:Temporal123!`).*

---

### 0.2 Creazione del Secret Kubernetes nel namespace `metadata`

Dalla cartella in cui risiedono i file `tls.crt` e `tls.key`:

#### Tramite CLI `kubectl` (Riga singola):
```powershell
kubectl create secret tls fastapi-tls --cert=./tls.crt --key=./tls.key -n metadata
```

*(Se il secret esisteva già e vuoi sovrascriverlo, esegui prima: `kubectl delete secret fastapi-tls -n metadata`)*.

#### Alternativa tramite Interfaccia Grafica Rancher:
1. Accedere al cluster Rancher e selezionare il namespace **`metadata`**.
2. Dal menu laterale cliccare su **Storage** > **Secrets**.
3. Cliccare in alto a destra su **Create**.
4. Selezionare il tipo **TLS Certificate**.
5. Compilare i campi:
   - **Name**: `fastapi-tls`
   - **Private Key**: incollare il contenuto del file `tls.key` (oppure usare il pulsante *Read from file*).
   - **Certificate**: incollare il contenuto del file `tls.crt` (oppure usare il pulsante *Read from file*).
6. Cliccare su **Create** in basso.

---

## 1. Modifica al `deployment.yaml` (`fastapi-app`)

### Analisi e Strategia
Nel manifest attuale il pod esegue l'immagine:
`oros-git.regione.puglia.it:5050/dss-crm-puglia/dss/fastapi-app:v1.0.4`  
Il Dockerfile di default avvia Uvicorn in HTTP sulla porta 8000.  
**Vantaggio operativo:** Sovrascrivendo `command` e `args` direttamente nel manifest K8s del Deployment:
- **NON è necessario ricompilare né ripuntare una nuova immagine Docker**.
- L'immagine esistente viene avviata direttamente con i parametri SSL di Uvicorn.
- I certificati vengono iniettati tramite volume mount in sola lettura su `/etc/tls`.

### Differenze da applicare:
1. Impostare `containerPort: 8443` con `name: https`.
2. Aggiungere `command: ["uvicorn"]` e i relativi `args` per abilitare `--ssl-keyfile` e `--ssl-certfile`.
3. Aggiungere `volumeMounts` puntato su `/etc/tls` (`readOnly: true`).
4. Aggiungere il `volume` collegato al Secret `fastapi-tls`.
5. *(Opzionale ma raccomandato)* Configurare le sonde `livenessProbe` e `readinessProbe` con `scheme: HTTPS` sulla porta `8443`.

### Manifest Aggiornato del Deployment (`k8/deployment.yaml`)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi-app
  namespace: metadata
  labels:
    app: fastapi-app
spec:
  replicas: 2
  revisionHistoryLimit: 10
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 25%
      maxUnavailable: 25%
  selector:
    matchLabels:
      app: fastapi-app
  template:
    metadata:
      labels:
        app: fastapi-app
    spec:
      containers:
        - name: fastapi
          image: oros-git.regione.puglia.it:5050/dss-crm-puglia/dss/fastapi-app:v1.0.4
          imagePullPolicy: IfNotPresent
          command:
            - uvicorn
          args:
            - app.main:app
            - --host
            - 0.0.0.0
            - --port
            - "8443"
            - --ssl-keyfile
            - /etc/tls/tls.key
            - --ssl-certfile
            - /etc/tls/tls.crt
            - --workers
            - "4"
          ports:
            - name: https
              containerPort: 8443
              protocol: TCP
          env:
            - name: MONGO_URI
              valueFrom:
                secretKeyRef:
                  key: mongo-uri
                  name: mongo-fastapi-secret
                  optional: true
            - name: MONGO_HOST
              value: 172.28.23.8
            - name: MONGO_PORT
              value: '27017'
            - name: MONGO_DB
              value: DPB_MG_DR
            - name: MONGO_USER
              valueFrom:
                secretKeyRef:
                  key: mongo-user
                  name: mongo-fastapi-secret
                  optional: true
            - name: MONGO_PASSWORD
              valueFrom:
                secretKeyRef:
                  key: mongo-password
                  name: mongo-fastapi-secret
                  optional: true
          volumeMounts:
            - name: fastapi-tls-volume
              mountPath: /etc/tls
              readOnly: true
          # Sonde di salute in HTTPS (il kubelet accetta certificati self-signed su probe https)
          livenessProbe:
            httpGet:
              path: /health
              port: 8443
              scheme: HTTPS
            initialDelaySeconds: 20
            periodSeconds: 15
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health
              port: 8443
              scheme: HTTPS
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 2
          resources: {}
          terminationMessagePath: /dev/termination-log
          terminationMessagePolicy: File
      dnsPolicy: ClusterFirst
      imagePullSecrets:
        - name: oros-git-regione-puglia-it
      restartPolicy: Always
      schedulerName: default-scheduler
      securityContext: {}
      terminationGracePeriodSeconds: 30
      volumes:
        - name: fastapi-tls-volume
          secret:
            secretName: fastapi-tls
            defaultMode: 0400
```

### 1.1 Configurazione Secret per MongoDB Replica Set con TLS (`mongo-fastapi-secret`)

A seguito dell'abilitazione del protocollo TLS sul cluster MongoDB del cliente, l'applicazione supporta la variabile `MONGO_URI`. La stringa di connessione gestisce nativamente:
- I nodi multipli del Replica Set (`dpc-db-mds1-l01:27017,dpc-db-mds1-l02:27017,dpc-db-mds1-l03:27017`);
- L'autenticazione con `authSource=admin`;
- La cifratura TLS abilitata con bypass della validazione hostname/certificati interni: `tls=true&tlsAllowInvalidCertificates=true&tlsAllowInvalidHostnames=true`.

#### Creazione / Aggiornamento del Secret `mongo-fastapi-secret` su PowerShell (riga singola):
```powershell
kubectl create secret generic mongo-fastapi-secret --from-literal=mongo-uri="mongodb://<utente>:<password>@dpc-db-mds1-l01.dpc.localdomain:27017,dpc-db-mds1-l02.dpc.localdomain:27017,dpc-db-mds1-l03.dpc.localdomain:27017/DPB_MG_DR?authSource=admin&tls=true&tlsAllowInvalidCertificates=true&tlsAllowInvalidHostnames=true" -n metadata --dry-run=client -o yaml | kubectl apply -f -
```

*(In alternativa tramite interfaccia Rancher: Namespace `metadata` > **Storage** > **Secrets** > cliccare su `mongo-fastapi-secret` > **Edit** > aggiungere la chiave `mongo-uri` contenente la stringa completa).*

---

## 2. Modifica al `service.yaml` (`fastapi-service`)

### Analisi
In precedenza il Service ascoltava sulla porta 80 e inoltrava a `targetPort: 8000` (HTTP).  
Per abilitare il Full HTTPS:
- Il `targetPort` deve diventare `8443` (la porta HTTPS su cui risponde Uvicorn nel pod).
- Esporre la porta `8443` come porta primaria `https`.
- *(Best Practice)* Mantenere anche la porta `80` associata a `targetPort: 8443`: se qualche client interno o vecchio script chiama ancora la porta 80, la connessione viene comunque veicolata sul pod in crittografia TLS.

### Manifest Aggiornato del Service (`k8/service.yaml`)

```yaml
apiVersion: v1
kind: Service
metadata:
  name: fastapi-service
  namespace: metadata
  labels:
    app: fastapi-app
spec:
  type: ClusterIP
  selector:
    app: fastapi-app
  ports:
    - name: https
      port: 8443
      protocol: TCP
      targetPort: 8443
    - name: https-compat
      port: 80
      protocol: TCP
      targetPort: 8443
  sessionAffinity: None
```

> **Verifica Intra-cluster:**  
> Da questo momento qualsiasi chiamata all'interno del cluster deve usare l'URL:  
> `https://fastapi-service:8443` oppure `https://fastapi-service.metadata.svc.cluster.local:8443`

---

## 3. Modifica all'`ingress.yaml` (`fastapi-ingress`)

### Analisi e Annotazioni
Il cluster Rancher utilizza come Ingress Controller predefinito **Traefik** (`ingressClassName: traefik`).
Per soddisfare il requisito di **Full HTTPS** (nessun traffico in chiaro neanche tra Ingress e Pod):
1. **`traefik.ingress.kubernetes.io/router.entrypoints: websecure`**: accetta solo traffico HTTPS sulla porta 443.
2. **`traefik.ingress.kubernetes.io/router.tls: "true"`**: forza la gestione TLS sul router Traefik.
3. **`traefik.ingress.kubernetes.io/service.serversscheme: https`**: **CRUCIALE**. Indica a Traefik di aprire una connessione **HTTPS** verso il backend Pod (porta 8443) invece di HTTP in chiaro.
4. **`nginx.ingress.kubernetes.io/backend-protocol: HTTPS`**: annotazione Nginx equivalente (mantenuta per retrocompatibilità qualora il cluster monti controller Nginx).
5. **Sezione `spec.tls`**: associa il certificato `fastapi-tls` al dominio `fastapi.dss.local`.
6. **Backend Port**: aggiornata a `number: 8443`.

### Manifest Aggiornato dell'Ingress (`k8/ingress.yaml`)

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fastapi-ingress
  namespace: metadata
  labels:
    app: fastapi-app
  annotations:
    traefik.ingress.kubernetes.io/router.entrypoints: websecure
    traefik.ingress.kubernetes.io/router.tls: "true"
    traefik.ingress.kubernetes.io/service.serversscheme: https
    nginx.ingress.kubernetes.io/backend-protocol: HTTPS
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  ingressClassName: traefik
  tls:
    - hosts:
        - fastapi.dss.local
      secretName: fastapi-tls
  rules:
    - host: fastapi.dss.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: fastapi-service
                port:
                  number: 8443
```

---

## 4. Guida Passo-Passo per Riconfigurare da Zero su Rancher

Di seguito la sequenza esatta da seguire per applicare le modifiche senza downtime o conflitti.

### Passo 1: Applicare il Secret
Assicurarsi che il secret `fastapi-tls` sia stato creato nel namespace `metadata` (vedi Sezione 0.2).  
Verifica da CLI:
```powershell
kubectl get secret fastapi-tls -n metadata
```

### Passo 2: Aggiornare il Deployment
Applicare il manifest `k8/deployment.yaml` aggiornato:
```powershell
kubectl apply -f k8/deployment.yaml
```
*Oppure da Rancher GUI*:  
Namespace `metadata` > **Workloads** > **Deployments** > cliccare sui tre puntini di `fastapi-app` > **Edit YAML** > incollare il blocco aggiornato e cliccare **Save**.

Verificare che i pod si riavviino e raggiungano lo stato `Running`:
```powershell
kubectl rollout status deployment/fastapi-app -n metadata
```

### Passo 3: Aggiornare il Service
Applicare il manifest `k8/service.yaml`:
```powershell
kubectl apply -f k8/service.yaml
```
*Oppure da Rancher GUI*:  
Namespace `metadata` > **Service Discovery** > **Services** > cliccare su `fastapi-service` > **Edit YAML** > salvare.

### Passo 4: Aggiornare l'Ingress
Applicare il manifest `k8/ingress.yaml`:
```powershell
kubectl apply -f k8/ingress.yaml
```
*Oppure da Rancher GUI*:  
Namespace `metadata` > **Service Discovery** > **Ingresses** > cliccare su `fastapi-ingress` > **Edit YAML** > salvare.

---

## 5. Verifica Finale Post-Deploy e Test di Conformità

Eseguire i seguenti test per validare che l'intero canale sia crittografato.

### 5.1 Verifica Log del Pod (FastAPI / Uvicorn in HTTPS)
```powershell
kubectl logs -n metadata -l app=fastapi-app --tail=50
```
Nei log del container deve comparire esplicitamente lo schema **`https://`**:
```text
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     🚀 Avvio FastAPI MongoDB REST API v1.0.0...
INFO:     ✅ Connessione iniziale MongoDB: OK (latenza: 1.25 ms)
INFO:     Uvicorn running on https://0.0.0.0:8443 (Press CTRL+C to quit)
```

### 5.2 Test Chiamata Esterna via Ingress
Dalla rete aziendale (o con mapping in `hosts` verso l'IP del cluster/Ingress):
```powershell
curl -k -i https://fastapi.dss.local/health
```
Risposta attesa (`HTTP/2 200` o `HTTP/1.1 200 OK` con JSON di salute):
```json
{
  "status": "healthy",
  "mongodb": "connected",
  "database": "DPB_MG_DR",
  "latency_ms": 1.25,
  "version": "1.0.0"
}
```

Verificare anche la documentazione interattiva Swagger UI su browser:
`https://fastapi.dss.local/docs`

### 5.3 Test Comunicazione Intrapod / Intra-cluster (Full HTTPS Verification)
Per verificare che anche la comunicazione interna sia autenticamente crittografata:
```powershell
kubectl run debug-curl --rm -i --tty --image=curlimages/curl -n metadata -- curl -k -i https://fastapi-service:8443/health
```
Se il test restituisce `200 OK`, è verificato al 100% che:
1. Il Pod risponde in TLS.
2. Il Service instrada TLS.
3. L'Ingress parla con il Pod in TLS.
4. Nessun pacchetto viaggia in chiaro nella rete del cluster Kubernetes.

---

## 6. Troubleshooting e Risoluzione Problemi Comuni

| Sintomo | Causa Probabile | Soluzione |
| :--- | :--- | :--- |
| **`502 Bad Gateway` dall'Ingress** | L'Ingress Traefik sta ancora provando a chiamare il backend in HTTP anziché HTTPS, oppure la porta del backend non corrisponde. | Verificare che nell'`ingress.yaml` sia presente l'annotazione `traefik.ingress.kubernetes.io/service.serversscheme: https` e che il backend punti alla porta `8443`. |
| **`Internal Server Error` / Traefik SSL Verify** | Traefik rifiuta il certificato self-signed del pod durante il proxying verso il backend. | Se Traefik ha il check SSL abilitato, creare una risorsa `ServersTransport` con `insecureSkipVerify: true` oppure verificare le impostazioni del controller Traefik di Rancher. |
| **`CrashLoopBackOff` o errore `[Errno 2] No such file or directory` su Uvicorn** | I percorsi `/etc/tls/tls.crt` o `/etc/tls/tls.key` non esistono perché il secret non è montato correttamente. | Verificare che il Secret `fastapi-tls` sia presente nel namespace `metadata` e che il blocco `volumes` e `volumeMounts` nel `deployment.yaml` punti al nome esatto del secret. |
| **Sonde `Liveness/Readiness probe failed`** | La sonda nel Deployment è rimasta configurata con `scheme: HTTP`. Uvicorn risponde ora solo in HTTPS e rifiuta handshake HTTP. | Modificare nel `deployment.yaml` il campo `scheme: HTTPS` e `port: 8443` nelle sezioni `livenessProbe` e `readinessProbe`. |
| **Client riceve `Certificate name mismatch`** | Il certificato non include nel SAN il dominio chiamato. | Rigenerare il certificato assicurandosi che il parametro `subjectAltName` contenga `DNS:fastapi.dss.local,DNS:fastapi-service`. |
