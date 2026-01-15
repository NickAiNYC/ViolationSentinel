"""
Stripe Webhook Handler
Processes subscription payments and updates user tiers
"""

from fastapi import FastAPI, Request, HTTPException
import stripe
import os
import json
from datetime import datetime

app = FastAPI(title="ViolationSentinel Stripe Webhooks")

# Stripe configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_...")
webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_...")

# In-memory database (in production, use Supabase)
users_db = {}


@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events
    
    Events handled:
    - checkout.session.completed: New subscription
    - customer.subscription.updated: Subscription changed
    - customer.subscription.deleted: Subscription cancelled
    - invoice.payment_succeeded: Payment succeeded
    - invoice.payment_failed: Payment failed
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # Handle the event
    event_type = event["type"]
    data = event["data"]["object"]
    
    print(f"Received event: {event_type}")
    
    if event_type == "checkout.session.completed":
        # New subscription created
        handle_checkout_completed(data)
        
    elif event_type == "customer.subscription.updated":
        # Subscription updated (upgrade/downgrade)
        handle_subscription_updated(data)
        
    elif event_type == "customer.subscription.deleted":
        # Subscription cancelled
        handle_subscription_deleted(data)
        
    elif event_type == "invoice.payment_succeeded":
        # Payment succeeded
        handle_payment_succeeded(data)
        
    elif event_type == "invoice.payment_failed":
        # Payment failed
        handle_payment_failed(data)
    
    return {"status": "success"}


def handle_checkout_completed(session):
    """Handle successful checkout"""
    customer_email = session.get("customer_email")
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    
    print(f"New subscription for {customer_email}")
    
    # Update user tier to Pro
    users_db[customer_email] = {
        "tier": "pro",
        "stripe_customer_id": customer_id,
        "stripe_subscription_id": subscription_id,
        "buildings_limit": 999999,
        "subscribed_at": datetime.utcnow().isoformat(),
        "status": "active"
    }
    
    # TODO: Send welcome email
    # TODO: Update Supabase database
    
    print(f"Updated {customer_email} to Pro tier")


def handle_subscription_updated(subscription):
    """Handle subscription update"""
    customer_id = subscription.get("customer")
    status = subscription.get("status")
    
    print(f"Subscription updated for customer {customer_id}: {status}")
    
    # Find user by customer_id
    for email, user in users_db.items():
        if user.get("stripe_customer_id") == customer_id:
            user["status"] = status
            
            # If cancelled, downgrade to free after period ends
            if status == "canceled":
                user["tier"] = "free"
                user["buildings_limit"] = 3
                print(f"Downgraded {email} to free tier")
            
            break


def handle_subscription_deleted(subscription):
    """Handle subscription cancellation"""
    customer_id = subscription.get("customer")
    
    print(f"Subscription deleted for customer {customer_id}")
    
    # Downgrade user to free tier
    for email, user in users_db.items():
        if user.get("stripe_customer_id") == customer_id:
            user["tier"] = "free"
            user["buildings_limit"] = 3
            user["status"] = "cancelled"
            print(f"Downgraded {email} to free tier")
            break


def handle_payment_succeeded(invoice):
    """Handle successful payment"""
    customer_id = invoice.get("customer")
    amount_paid = invoice.get("amount_paid") / 100  # Convert from cents
    
    print(f"Payment succeeded for customer {customer_id}: ${amount_paid}")
    
    # TODO: Send payment receipt email
    # TODO: Log payment in database


def handle_payment_failed(invoice):
    """Handle failed payment"""
    customer_id = invoice.get("customer")
    
    print(f"Payment failed for customer {customer_id}")
    
    # Find user and send payment failure email
    for email, user in users_db.items():
        if user.get("stripe_customer_id") == customer_id:
            # TODO: Send payment failure email
            # TODO: Mark account as past due
            print(f"Payment failed for {email}")
            break


@app.get("/")
def home():
    """Health check"""
    return {"status": "Stripe webhook handler running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
