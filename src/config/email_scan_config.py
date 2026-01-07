from typing import Dict, List
from datetime import datetime, timedelta


class EmailScanConfig:
    
    EMAIL_TYPES = {
        "bills": {
            "name": "Bills & Invoices",
            "keywords": [
                "invoice", "bill", "statement", "payment due", "amount due",
                "balance due", "billing statement", "account statement",
                "monthly statement", "payment reminder", "past due", "overdue"
            ],
            "subject_patterns": [
                "invoice", "bill", "statement", "payment", "due"
            ],
            "default_days": 30,
            "description": "Bills, invoices, and payment statements"
        },
        
        "promotions": {
            "name": "Promotions & Offers",
            "keywords": [
                "offer", "promotion", "sale", "discount", "deal",
                "limited time", "exclusive offer", "special offer",
                "save now", "flash sale", "clearance", "promo code"
            ],
            "subject_patterns": [
                "offer", "sale", "discount", "deal", "promo"
            ],
            "default_days": 7,
            "description": "Promotional emails and special offers"
        },
        
        "discounts": {
            "name": "Discount Codes & Coupons",
            "keywords": [
                "coupon", "discount code", "promo code", "voucher",
                "save", "% off", "percent off", "code:", "use code",
                "redeem", "coupon code", "discount voucher"
            ],
            "subject_patterns": [
                "coupon", "code", "discount", "save", "voucher"
            ],
            "default_days": 14,
            "description": "Discount codes, coupons, and vouchers"
        },
        
        "orders": {
            "name": "Order Confirmations",
            "keywords": [
                "order confirmation", "order received", "order placed",
                "thank you for your order", "order number", "order #",
                "purchase confirmation", "order details", "your order"
            ],
            "subject_patterns": [
                "order", "confirmation", "purchase", "receipt"
            ],
            "default_days": 30,
            "description": "Order confirmations and purchase receipts"
        },
        
        "shipping": {
            "name": "Shipping & Delivery",
            "keywords": [
                "shipped", "tracking", "delivery", "out for delivery",
                "tracking number", "package", "dispatched", "in transit",
                "delivered", "carrier", "tracking info", "shipment"
            ],
            "subject_patterns": [
                "shipped", "tracking", "delivery", "package"
            ],
            "default_days": 21,
            "description": "Shipping notifications and tracking updates"
        },
        
        "receipts": {
            "name": "Payment Receipts",
            "keywords": [
                "receipt", "payment received", "payment confirmation",
                "transaction", "paid", "payment successful", "thank you for your payment",
                "payment processed", "confirmation of payment"
            ],
            "subject_patterns": [
                "receipt", "payment", "transaction", "paid"
            ],
            "default_days": 30,
            "description": "Payment receipts and transaction confirmations"
        },
        
        "subscriptions": {
            "name": "Subscription Renewals",
            "keywords": [
                "subscription", "renewal", "renew", "auto-renew",
                "membership", "subscription renewal", "plan renewal",
                "subscription expires", "subscription ending", "renew now"
            ],
            "subject_patterns": [
                "subscription", "renewal", "membership", "renew"
            ],
            "default_days": 60,
            "description": "Subscription renewals and membership notices"
        },
        
        "universities": {
            "name": "University Communications",
            "keywords": [
                "admission", "offer letter", "acceptance letter", "university",
                "college", "enrollment", "admission offer", "congratulations",
                "admitted", "application status", "decision letter", "scholarship",
                "tuition", "financial aid", "student", "academic"
            ],
            "subject_patterns": [
                "admission", "offer", "acceptance", "university", "college"
            ],
            "default_days": 90,
            "description": "University admissions, offer letters, and academic communications"
        },
        
        "tax": {
            "name": "Tax Documents",
            "keywords": [
                "tax", "1099", "W-2", "tax form", "tax document",
                "tax statement", "annual statement", "year-end statement",
                "tax return", "IRS", "HMRC", "tax filing"
            ],
            "subject_patterns": [
                "tax", "1099", "W-2", "annual statement"
            ],
            "default_days": 365,
            "description": "Tax documents and annual statements"
        },
        
        "travel": {
            "name": "Travel & Bookings",
            "keywords": [
                "booking confirmation", "reservation", "flight", "hotel",
                "travel", "itinerary", "boarding pass", "check-in",
                "booking reference", "confirmation number", "trip"
            ],
            "subject_patterns": [
                "booking", "reservation", "flight", "hotel", "travel"
            ],
            "default_days": 60,
            "description": "Travel bookings, reservations, and itineraries"
        },
        
        "insurance": {
            "name": "Insurance Documents",
            "keywords": [
                "insurance", "policy", "coverage", "premium",
                "claim", "insurance policy", "policy renewal",
                "insurance document", "insurance statement", "deductible"
            ],
            "subject_patterns": [
                "insurance", "policy", "coverage", "premium"
            ],
            "default_days": 90,
            "description": "Insurance policies, claims, and renewals"
        },
        
        "banking": {
            "name": "Banking & Finance",
            "keywords": [
                "bank statement", "account summary", "balance",
                "transaction alert", "deposit", "withdrawal", "transfer",
                "credit card", "debit card", "account activity"
            ],
            "subject_patterns": [
                "bank", "account", "balance", "transaction"
            ],
            "default_days": 30,
            "description": "Bank statements and financial alerts"
        }
    }
    
    NATURAL_LANGUAGE_ALIASES = {
        "bills": ["bill", "invoice", "invoices", "payment", "payments"],
        "promotions": ["promo", "promos", "offer", "offers", "promotion", "sale", "sales"],
        "discounts": ["discount", "coupon", "coupons", "code", "codes"],
        "orders": ["order", "purchase", "purchases", "bought"],
        "shipping": ["ship", "delivery", "deliveries", "tracking", "package", "packages"],
        "receipts": ["receipt", "confirmation", "confirmations"],
        "subscriptions": ["subscription", "membership", "memberships", "renew", "renewal"],
        "universities": ["university", "college", "admission", "admissions", "offer letter", "acceptance"],
        "tax": ["tax", "taxes", "1099", "w2", "w-2"],
        "travel": ["travel", "flight", "flights", "hotel", "hotels", "booking", "bookings"],
        "insurance": ["insurance", "policy", "policies"],
        "banking": ["bank", "banking", "statement", "statements"]
    }
    
    TIME_PATTERNS = {
        "today": 1,
        "yesterday": 2,
        "this week": 7,
        "last week": 14,
        "this month": 30,
        "last month": 60,
        "last 3 months": 90,
        "last 6 months": 180,
        "this year": 365
    }
    
    @classmethod
    def get_email_type(cls, type_key: str) -> Dict:
        return cls.EMAIL_TYPES.get(type_key.lower())
    
    @classmethod
    def get_all_types(cls) -> List[str]:
        return list(cls.EMAIL_TYPES.keys())
    
    @classmethod
    def get_type_names(cls) -> Dict[str, str]:
        return {key: config["name"] for key, config in cls.EMAIL_TYPES.items()}
    
    @classmethod
    def parse_natural_language(cls, query: str) -> Dict:
        query_lower = query.lower()
        
        detected_type = None
        detected_days = None
        
        for type_key, aliases in cls.NATURAL_LANGUAGE_ALIASES.items():
            for alias in aliases:
                if alias in query_lower:
                    detected_type = type_key
                    break
            if detected_type:
                break
        
        for time_phrase, days in cls.TIME_PATTERNS.items():
            if time_phrase in query_lower:
                detected_days = days
                break
        
        if not detected_type:
            detected_type = "bills"
        
        if not detected_days and detected_type:
            detected_days = cls.EMAIL_TYPES[detected_type]["default_days"]
        
        return {
            "type": detected_type,
            "days": detected_days or 30,
            "keywords": cls.EMAIL_TYPES[detected_type]["keywords"]
        }
    
    @classmethod
    def get_config_summary(cls) -> str:
        summary = "\n📧 Email Scan Types Available:\n\n"
        for key, config in cls.EMAIL_TYPES.items():
            summary += f"  {key:15} - {config['name']}\n"
            summary += f"  {'':15}   {config['description']}\n"
            summary += f"  {'':15}   Default: {config['default_days']} days\n\n"
        return summary
    
    @classmethod
    def validate_type(cls, type_key: str) -> bool:
        return type_key.lower() in cls.EMAIL_TYPES


config = EmailScanConfig()