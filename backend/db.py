from peewee import *
import datetime
import os

# Database file in the backend directory
db_path = os.path.join(os.path.dirname(__file__), 'aeternus.db')
db = SqliteDatabase(db_path)

class BaseModel(Model):
    class Meta:
        database = db

class Transaction(BaseModel):
    """Stores both real payments and agent intelligence actions."""
    title = CharField()
    category = CharField() # 'Investment', 'Payment', 'Intelligence', 'Security'
    description = TextField(null=True)
    amount = FloatField(null=True)
    currency = CharField(default='INR')
    status = CharField(default='Pending') # 'Completed', 'Verified', 'Failed', 'Pending'
    icon = CharField(default='receipt_long')
    timestamp = DateTimeField(default=datetime.datetime.now)
    is_positive = BooleanField(default=False)
    source = CharField(default='Agent') # 'User', 'Agent', 'Paytm'

def init_db():
    db.connect()
    db.create_tables([Transaction])
    
    # Add seed data if empty
    if Transaction.select().count() == 0:
        Transaction.create(
            title="NIFTY 50 Analysis",
            category="Intelligence",
            description="Analyzed market volatility and identified bullish patterns.",
            status="Completed",
            icon="psychology",
            is_positive=True,
            source="Agent"
        )
        Transaction.create(
            title="Beneficiary Verification",
            category="Security",
            description="Verified UPI ID: rahul@paytm for Rahul Sharma.",
            status="Verified",
            icon="verified_user",
            source="Agent"
        )

if __name__ == "__main__":
    init_db()
    print(f"Database initialized at {db_path}")
