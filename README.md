# Personal Tarot WhatsApp Service

## 📖 What is this project about?

This project is a WhatsApp-based **personal tarot reading service**.  
Users subscribe through a recurring payment and receive:
- A **weekly personalized tarot reading** via WhatsApp (text, image, and optionally voice message).
- The right to ask **3 personal questions per month**, answered with tarot insights.


## 📸 Architecture

![Architecture Diagram](ArchitectureDiagram.png)

## System Architecture

The Tarot Bot system is designed to provide a seamless experience for users interacting via WhatsApp. It integrates multiple cloud services to handle messaging, dynamic tarot reading generation, user management, and payment processing.

### Architecture Overview

- **User Interaction (WhatsApp)**:  
  Users interact with the bot through WhatsApp. All incoming and outgoing messages are managed through Twilio's WhatsApp API.

- **Twilio API**:  
  Twilio handles message delivery and reception. Incoming user messages are forwarded to the backend, and responses are sent back via Twilio. The user's phone number is used as their unique identifier across the system.

- **Backend (FastAPI)**:  
  The FastAPI server processes webhook events from Twilio (incoming messages) and Stripe/PayPal (payment updates). It interacts with Firebase to manage user state, track subscription status, and trigger OpenAI for dynamic tarot readings.

- **Firebase**:  
  Firebase serves as the real-time database and user management system. It stores user profiles, subscription status, questions, answers, and the next eligible consultation date.

- **Stripe API (or PayPal)**:  
  Stripe or PayPal handles recurring billing. Payment success or failure events are sent via webhooks to the backend, which updates user subscription data in Firebase accordingly.

- **OpenAI API (ChatGPT)**:  
  The backend calls OpenAI’s API to generate customized tarot readings based on randomly selected cards or user-submitted questions.

- **Scheduled Messages (Weekly Tarot Readings)**:  
  Every Sunday or Monday, the backend fetches active users from Firebase and sends a weekly tarot insight via Twilio.

- **Error Handling and Logging**:  
  All major actions (payment processing, message handling, AI responses) are logged to ensure reliability, monitor failures, and aid in debugging.

### Key Data Flows

1. **User sends a message → Twilio Webhook → Backend → Firebase Check → AI Generation → Reply via Twilio**  
2. **User subscribes → Stripe/PayPal Payment → Payment Webhook → Backend → Update Firebase**  
3. **Scheduled event → Backend fetches active users → Generate weekly reading → Send via Twilio**


The service integrates:
- WhatsApp communication (Twilio API)
- Payment processing (PayPal/Stripe Webhooks)
- Firebase for user management
- FastAPI backend
- OpenAI for text generation
- ElevenLabs or Google TTS for voice synthesis

---

## ⚙️ How it works

1. User sees an ad and sends a WhatsApp message.
2. The system identifies the user and explains the service.
3. User clicks a link to subscribe with a recurring payment.
4. Upon payment confirmation:
   - The user is registered as active in Firebase.
   - A welcome message is sent.
5. Every Sunday:
   - A random tarot reading is generated and sent to all active users.
6. Once a month:
   - User can send "Pergunta" followed by their three questions.
   - The system generates personalized readings and sends them back.
7. Users can cancel anytime by sending "Cancelar".

---

## 🚀 How to install and run locally

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/personal-tarot.git
cd personal-tarot
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # Mac/Linux
# ou
.venv\Scripts\activate  # Windows
```

### 3. Install the requirements

```bash
pip install -r requirements.txt
```

### 4. Set up your environment variables

Create a `.env` file in the project root with:

```bash
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+your_twilio_number
OPENAI_API_KEY=your_openai_key
FIREBASE_CREDENTIALS_PATH=path_to_your_firebase_credentials.json
PAYPAL_WEBHOOK_ID=your_paypal_webhook_id
PAYPAL_CLIENT_ID=your_paypal_client_id
PAYPAL_CLIENT_SECRET=your_paypal_client_secret
VOICE_API_KEY=your_elevenlabs_or_googlecloud_key
```

> ⚠️ Never commit your `.env` to Git!

### 5. Run the application

```bash
uvicorn app.main:app --reload
```

The app will be available at `http://localhost:8000`.

---

## 📬 Webhooks setup

- WhatsApp (Twilio): Set webhook to `https://your-app-url.com/webhook/message`
- Payment (PayPal/Stripe): Set webhook to `https://your-app-url.com/webhook/payment`

---

## 📦 Deployment (Render, Railway, Fly.io, etc.)

1. Push your code to GitHub.
2. Connect the repo to your chosen platform.
3. Set environment variables in the platform dashboard.
4. Enable automatic deploys.

---

## 📄 License

MIT License - feel free to use and adapt.

---

## 📸 Samples

![Sample 1](image1.png)
![Sample 2](image2.png)
