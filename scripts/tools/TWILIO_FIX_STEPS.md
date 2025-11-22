# Twilio SMS Fix - Step by Step Guide

## Current Status
✅ Code is working correctly  
✅ Messages are being sent to Twilio  
✅ Messaging Service is configured  
❌ **A2P 10DLC Campaign is NOT approved** (this is why messages are undelivered)

## Quick Fix Steps

### Step 1: Add Messaging Service SID to .env

Add this line to your `.env` file:

```
TWILIO_MESSAGING_SERVICE_SID=MGbc5e4ec741503c3cf6d15a291ca0985b
```

### Step 2: Register A2P 10DLC Campaign in Twilio Console

1. **Go to Twilio Console**: https://console.twilio.com/us1/develop/sms/services

2. **Click on your Messaging Service**: "Sole Proprietor A2P Messaging Service"

3. **Go to "A2P 10DLC" tab** (in the left sidebar)

4. **Check if you have a Brand Registration**:
   - If NO: Go to "Regulatory Compliance" → "Brand Registrations" → Create new brand
   - Fill out business information
   - Wait for approval (1-2 business days)

5. **Create A2P 10DLC Campaign**:
   - Click "Create Campaign" or "Register Campaign"
   - Select your brand
   - Choose campaign type:
     - **Mixed**: For general business communications
     - **Marketing**: For promotional messages
     - **2FA**: For authentication codes
   - Fill out campaign details
   - Submit for approval

6. **Wait for Approval**:
   - Status will show as "PENDING" → "APPROVED" → "ACTIVE"
   - This can take 1-2 business days
   - Once approved, SMS will start delivering

### Step 3: Verify Campaign Status

Run this to check status:

```bash
python scripts/tools/send_sms_to_user.py
```

Once campaign is approved, messages should show status "delivered" instead of "undelivered".

## Alternative: Use Toll-Free Number

If A2P 10DLC registration is not feasible, you can use a **Toll-Free Number** which doesn't require A2P 10DLC:

1. Purchase a Toll-Free number in Twilio Console
2. Update `.env`:
   ```
   TWILIO_PHONE_NUMBER=+1XXXXXXXXXX  # Your toll-free number
   ```
3. Remove or comment out `TWILIO_MESSAGING_SERVICE_SID`
4. Code will automatically use the toll-free number

## What's Happening Now

- ✅ Your code is correctly sending messages to Twilio
- ✅ Twilio is accepting the messages (status: "queued")
- ❌ Carriers are rejecting delivery because there's no approved A2P 10DLC campaign
- ❌ Messages show as "undelivered" with error 30034

Once you complete the A2P 10DLC campaign registration and get approval, all messages will start delivering successfully.

## Need Help?

- Twilio Support: https://support.twilio.com/
- A2P 10DLC Guide: https://www.twilio.com/docs/messaging/a2p-10dlc
- Error 30034: https://www.twilio.com/docs/api/errors/30034

