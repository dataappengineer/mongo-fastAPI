"""
Script to seed MongoDB with test data.
Run this after starting the MongoDB container to populate test collections.
"""
import os
import sys
from datetime import datetime, timedelta
from pymongo import MongoClient
from pymongo.errors import PyMongoError

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def seed_database():
    """Seed the database with test collections."""
    
    # Connection settings
    mongo_host = os.getenv("MONGO_HOST", "localhost")
    mongo_port = int(os.getenv("MONGO_PORT", "27017"))
    mongo_db = os.getenv("MONGO_DB", "testdb")
    
    print(f"🔌 Connecting to MongoDB at {mongo_host}:{mongo_port}...")
    
    try:
        # Connect to MongoDB
        client = MongoClient(f"mongodb://{mongo_host}:{mongo_port}/")
        db = client[mongo_db]
        
        print(f"✅ Connected to database: {mongo_db}")
        
        # Drop existing collections if they exist
        print("🗑️  Dropping existing test collections...")
        db.customers.drop()
        db.products.drop()
        db.orders.drop()
        
        # Collection 1: Customers
        print("📝 Creating 'customers' collection...")
        customers = [
            {
                "customer_id": 1,
                "name": "Mario Rossi",
                "email": "mario.rossi@email.it",
                "age": 35,
                "city": "Roma",
                "active": True,
                "registration_date": datetime(2023, 1, 15),
                "total_purchases": 1250.50
            },
            {
                "customer_id": 2,
                "name": "Giulia Bianchi",
                "email": "giulia.bianchi@email.it",
                "age": 28,
                "city": "Milano",
                "active": True,
                "registration_date": datetime(2023, 3, 22),
                "total_purchases": 3400.75
            },
            {
                "customer_id": 3,
                "name": "Luca Verdi",
                "email": "luca.verdi@email.it",
                "age": 42,
                "city": "Napoli",
                "active": False,
                "registration_date": datetime(2022, 11, 8),
                "total_purchases": 890.00
            },
            {
                "customer_id": 4,
                "name": "Anna Ferrari",
                "email": "anna.ferrari@email.it",
                "age": 31,
                "city": "Torino",
                "active": True,
                "registration_date": datetime(2023, 5, 10),
                "total_purchases": 2150.25
            },
            {
                "customer_id": 5,
                "name": "Paolo Colombo",
                "email": "paolo.colombo@email.it",
                "age": None,  # Missing age to test null handling
                "city": "Firenze",
                "active": True,
                "registration_date": datetime(2023, 7, 3),
                "total_purchases": 670.80
            }
        ]
        db.customers.insert_many(customers)
        print(f"   ✅ Inserted {len(customers)} customers")
        
        # Collection 2: Products
        print("📝 Creating 'products' collection...")
        products = [
            {
                "product_id": 101,
                "name": "Laptop Dell XPS 15",
                "category": "Electronics",
                "price": 1299.99,
                "in_stock": True,
                "quantity": 15,
                "specs": {
                    "cpu": "Intel i7",
                    "ram": "16GB",
                    "storage": "512GB SSD"
                },
                "tags": ["laptop", "dell", "premium"]
            },
            {
                "product_id": 102,
                "name": "Mouse Logitech MX Master",
                "category": "Accessories",
                "price": 89.99,
                "in_stock": True,
                "quantity": 45,
                "specs": {
                    "wireless": True,
                    "dpi": 4000
                },
                "tags": ["mouse", "wireless", "ergonomic"]
            },
            {
                "product_id": 103,
                "name": "Monitor Samsung 27\"",
                "category": "Electronics",
                "price": 349.99,
                "in_stock": False,
                "quantity": 0,
                "specs": {
                    "size": "27 inch",
                    "resolution": "2560x1440",
                    "refresh_rate": "144Hz"
                },
                "tags": ["monitor", "gaming", "4K"]
            },
            {
                "product_id": 104,
                "name": "Tastiera Meccanica RGB",
                "category": "Accessories",
                "price": 129.99,
                "in_stock": True,
                "quantity": 30,
                "specs": {
                    "switches": "Cherry MX Red",
                    "backlight": "RGB"
                },
                "tags": ["keyboard", "mechanical", "gaming"]
            },
            {
                "product_id": 105,
                "name": "Webcam HD",
                "category": "Accessories",
                "price": 59.99,
                "in_stock": True,
                "quantity": 20,
                "specs": None,  # Null specs to test null handling
                "tags": ["webcam", "1080p"]
            }
        ]
        db.products.insert_many(products)
        print(f"   ✅ Inserted {len(products)} products")
        
        # Collection 3: Orders
        print("📝 Creating 'orders' collection...")
        orders = [
            {
                "order_id": 1001,
                "customer_id": 1,
                "order_date": datetime(2023, 6, 15, 10, 30),
                "status": "delivered",
                "items": [
                    {"product_id": 102, "quantity": 1, "price": 89.99},
                    {"product_id": 104, "quantity": 1, "price": 129.99}
                ],
                "total_amount": 219.98,
                "shipping_address": {
                    "street": "Via Roma 123",
                    "city": "Roma",
                    "postal_code": "00100"
                }
            },
            {
                "order_id": 1002,
                "customer_id": 2,
                "order_date": datetime(2023, 7, 20, 14, 15),
                "status": "shipped",
                "items": [
                    {"product_id": 101, "quantity": 1, "price": 1299.99}
                ],
                "total_amount": 1299.99,
                "shipping_address": {
                    "street": "Corso Buenos Aires 45",
                    "city": "Milano",
                    "postal_code": "20100"
                }
            },
            {
                "order_id": 1003,
                "customer_id": 4,
                "order_date": datetime(2023, 8, 5, 9, 45),
                "status": "processing",
                "items": [
                    {"product_id": 103, "quantity": 1, "price": 349.99},
                    {"product_id": 105, "quantity": 2, "price": 59.99}
                ],
                "total_amount": 469.97,
                "shipping_address": {
                    "street": "Via Po 78",
                    "city": "Torino",
                    "postal_code": "10100"
                }
            },
            {
                "order_id": 1004,
                "customer_id": 2,
                "order_date": datetime(2023, 8, 10, 16, 20),
                "status": "delivered",
                "items": [
                    {"product_id": 102, "quantity": 2, "price": 89.99},
                    {"product_id": 104, "quantity": 1, "price": 129.99}
                ],
                "total_amount": 309.97,
                "shipping_address": None  # Null address to test null handling
            },
            {
                "order_id": 1005,
                "customer_id": 5,
                "order_date": datetime(2023, 8, 12, 11, 0),
                "status": "pending",
                "items": [
                    {"product_id": 105, "quantity": 1, "price": 59.99}
                ],
                "total_amount": 59.99,
                "shipping_address": {
                    "street": "Piazza Signoria 9",
                    "city": "Firenze",
                    "postal_code": "50100"
                }
            }
        ]
        db.orders.insert_many(orders)
        print(f"   ✅ Inserted {len(orders)} orders")
        
        # Create indexes for better performance
        print("🔍 Creating indexes...")
        db.customers.create_index("customer_id", unique=True)
        db.customers.create_index("email", unique=True)
        db.products.create_index("product_id", unique=True)
        db.orders.create_index("order_id", unique=True)
        db.orders.create_index("customer_id")
        print("   ✅ Indexes created")
        
        # Summary
        print("\n" + "="*50)
        print("🎉 Database seeding completed successfully!")
        print("="*50)
        print(f"📊 Collections created:")
        print(f"   - customers: {db.customers.count_documents({})} documents")
        print(f"   - products: {db.products.count_documents({})} documents")
        print(f"   - orders: {db.orders.count_documents({})} documents")
        print("="*50)
        
        # Close connection
        client.close()
        
    except PyMongoError as e:
        print(f"❌ Error seeding database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    seed_database()
