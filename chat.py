# chat.py - ENHANCED WITH CONTEXTUAL INTELLIGENCE
import os
import time
import hashlib
from openai import OpenAI
from dotenv import load_dotenv
from retriever import retrieve
import traceback
import csv
import re

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

_response_cache = {}
CACHE_MAX_SIZE = 100

# Enhanced AI Persona for better understanding
SYSTEM_PERSONA = """
You are PALMS™ Salesbot, a friendly assistant for PALMS™ Warehouse Management. 

- Always start your response with a normal sentence introducing the topic. This first sentence must NEVER be a bullet point.  
- Only use bullet points for subsequent items if explicitly listing features, products, or clients (max 4 bullets).  
- Do not use bullet points for normal sentences or general explanations.  

- Use the provided chunks only as background knowledge.  
- Always give answers in complete sentences, even if the chunks are cut off.  
- Keep answers short, clear, warm, and approachable. Avoid jargon or overly technical language.  
- Use a conversational tone, like you are talking to a customer.  
- Your goal is to engage visitors, understand their needs, and encourage them to book a demo.  
- Respond politely, enthusiastically, and persuasively.  
- If needed, summarize long chunks into 2–3 sentences.  
- Always end your response with a gentle follow-up question, such as: 
  'Would you like to know more?', 'Should I connect you with our team?', or 'Would you like more details on this?'.  
- If a user requests a demo, respond with: "Kindly fill out the form to sign up for a demo."  
- If a user declines a demo, respond with: "No problem! Let me know if you have any other questions."

Example – correct response:
PALMS™ offers a variety of products designed to streamline warehouse management for businesses of all sizes.
- PALMS WMS: Core system for inventory and operations.
- PALMS 3PL: For third-party logistics providers.
Would you like to know more?

Example – incorrect response:
- PALMS™ offers a variety of products designed to streamline warehouse management for businesses of all sizes.
- PALMS WMS: Core system for inventory and operations.
Would you like to know more?
"""


def detect_demo_request(message):
    """
    Detect if user is asking for a demo based on keywords and context
    Returns True only if user is positively requesting a demo
    """
    message_lower = message.lower()
    
    # First check for negative indicators - if found, return False immediately
    negative_indicators = [
        "don't want", "dont want", "do not want", "not interested",
        "no demo", "no thank", "not now", "maybe later", "not ready",
        "don't need", "dont need", "do not need", "not looking",
        "no thanks", "not yet", "decline", "refuse", "not for me",
        "don't think", "dont think", "do not think", "not sure",
        "not what", "doesn't sound", "doesnt sound", "does not sound"
    ]
    
    for negative in negative_indicators:
        if negative in message_lower:
            return False
    
    # Check for negative patterns
    negative_patterns = [
        r'\b(no|not|don\'?t|do\s+not|never)\s+.*(demo|try|test|interested)\b',
        r'\b(maybe|perhaps|might)\s+(later|another\s+time)\b',
        r'\bnot\s+(ready|sure|interested|now)\b'
    ]
    
    for pattern in negative_patterns:
        if re.search(pattern, message_lower):
            return False
    
    # Now check for positive demo requests
    demo_keywords = [
        'demo', 'demonstration', 'trial', 'test drive', 
        'show me', 'try it', 'preview', 'walkthrough',
        'see how it works', 'want to see',
        'schedule a demo', 'book a demo', 'request demo',
        'free trial', 'pilot', 'poc', 'proof of concept'
    ]
    
    # Check if message contains demo-related keywords with positive intent
    positive_found = False
    for keyword in demo_keywords:
        if keyword in message_lower:
            positive_found = True
            break
    
    if not positive_found:
        # Check for positive question patterns
        positive_patterns = [
            r'\b(can|could|would)\s+.*(demo|try|test|see)\b',
            r'\b(show|demonstrate)\s+me\b',
            r'\bhow\s+(does|do)\s+.*(work|function)\b',
            r'\bi\s+(want|would\s+like)\s+to\s+(see|try|test)\b',
            r'\blet\s+me\s+(try|test|see)\b'
        ]
        
        for pattern in positive_patterns:
            if re.search(pattern, message_lower):
                positive_found = True
                break
    
    return positive_found

def get_query_hash(query):
    return hashlib.md5(query.lower().strip().encode()).hexdigest()

def build_intelligent_context(retrieved):
    """Build AI-friendly context from retrieved documents"""
    if not retrieved:
        return "No specific information available for this query."
    
    context_parts = []
    
    # Group by content type for better understanding
    feature_content = []
    client_content = []
    pricing_content = []
    technical_content = []
    general_content = []
    
    for result in retrieved:
        text = result.get('text', '')
        source = result.get('source_url') or result.get('source_file', 'unknown')
        relevance = result.get('relevance_score', 0)
        
        content_item = f"[Relevance: {relevance:.2f} | Source: {source}]\n{text}\n"
        
        # Categorize content for better AI understanding
        if any(keyword in text.lower() for keyword in ['feature', 'capability', 'function']):
            feature_content.append(content_item)
        elif any(keyword in text.lower() for keyword in ['client', 'customer', 'case study', 'testimonial']):
            client_content.append(content_item)
        elif any(keyword in text.lower() for keyword in ['price', 'cost', 'pricing', 'subscription']):
            pricing_content.append(content_item)
        elif any(keyword in text.lower() for keyword in ['technical', 'integration', 'api', 'compatible']):
            technical_content.append(content_item)
        else:
            general_content.append(content_item)
    
    # Build structured context
    if feature_content:
        context_parts.append("=== PRODUCT FEATURES ===\n" + "\n".join(feature_content[:3]))
    if client_content:
        context_parts.append("=== CLIENT SUCCESS ===\n" + "\n".join(client_content[:2]))
    if pricing_content:
        context_parts.append("=== PRICING INFORMATION ===\n" + "\n".join(pricing_content[:2]))
    if technical_content:
        context_parts.append("=== TECHNICAL DETAILS ===\n" + "\n".join(technical_content[:2]))
    if general_content:
        context_parts.append("=== GENERAL INFORMATION ===\n" + "\n".join(general_content[:3]))
    
    return "\n\n".join(context_parts)

def analyze_conversation_context(user_input, retrieved):
    """Analyze what type of conversation this is"""
    input_lower = user_input.lower()
    
    if any(word in input_lower for word in ['price', 'cost', 'how much', 'subscription']):
        return "pricing_inquiry"
    elif any(word in input_lower for word in ['feature', 'what can', 'capability', 'does it']):
        return "feature_inquiry" 
    elif any(word in input_lower for word in ['client', 'customer', 'case study', 'testimonial']):
        return "social_proof"
    elif any(word in input_lower for word in ['technical', 'integrate', 'api', 'compatible']):
        return "technical_inquiry"
    elif any(word in input_lower for word in ['demo', 'meeting', 'talk', 'contact']):
        return "conversion_request"
    else:
        return "general_inquiry"

LEADS_FILE = os.path.join(os.path.dirname(__file__), "leads.csv")

def save_lead(name, email):
    # Only write header if file is empty
    write_header = os.path.getsize(LEADS_FILE) == 0 if os.path.exists(LEADS_FILE) else True
    with open(LEADS_FILE, mode="a", newline="") as file:
        writer = csv.writer(file)
        if write_header:
            writer.writerow(["Name", "Email"])
        writer.writerow([name, email])

def is_business_email(email):
    # List of common personal email domains
    personal_domains = [
        "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com", "protonmail.com", "zoho.com"
    ]
    domain = email.split('@')[-1].lower()
    return not any(domain == d for d in personal_domains)

def format_list_response(text):
    # Detect list items separated by ' - ' or '\n- '
    items = []
    # Try splitting by ' - '
    if ' - ' in text:
        items = [i.strip() for i in text.split(' - ') if i.strip()]
    elif '\n- ' in text:
        items = [i.strip() for i in text.split('\n- ') if i.strip()]
    # If there are bullet points and a trailing question, separate the last sentence if it looks like a question
    if len(items) > 1:
        # Check if the last item is a question (ends with '?') and is a single sentence
        last_item = items[-1]
        if last_item.endswith('?') and (last_item.count('.') + last_item.count('!')) < 2:
            intro = items[0]
            bullets = items[1:-1]
            outro = last_item
            if bullets:
                return f'{intro}<ul>' + ''.join(f'<li>{item}</li>' for item in bullets) + f'</ul>{outro}'
            else:
                return f'{intro}<br>{outro}'
        else:
            intro = items[0]
            bullets = items[1:]
            return f'{intro}<ul>' + ''.join(f'<li>{item}</li>' for item in bullets) + '</ul>'
    return text

def get_chat_response(user_input, extra_context=''):
    try:
        # Detect greetings and company questions FIRST
        greetings = ["hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening"]
        is_greeting = any(greet in user_input.lower() for greet in greetings)
        is_company_question = "palms" in user_input.lower()
        wants_demo = detect_demo_request(user_input)

        # If greeting, return a simple greeting response
        if is_greeting:
            return {
                'response': "Hello! How can I assist you today?",
                'show_demo_popup': False,
                'show_options': False
            }
        # If demo requested, return demo response
        if wants_demo:
            return {
                'response': "I'd be happy to show you a demo of PALMS™! Our warehouse management system can really transform your operations. Please fill out the form below and we'll get you set up with a personalized demonstration.",
                'show_demo_popup': True,
                'show_options': False
            }
        # If company question, return a short hardcoded answer
        # REMOVED: if is_company_question:
        #     return {
        #         'response': "PALMS™ is a smart, scalable warehouse management system for modern businesses. It offers real-time inventory, fast order fulfillment, and easy integrations.",
        #         'show_demo_popup': False,
        #         'show_options': True
        #     }
        # Now, let AI analyze and respond to any question about PALMS
        # If user requests elaboration ("elaborate on:" or just "elaborate")
        user_input_stripped = user_input.strip().lower()
        if user_input_stripped.startswith("elaborate on:"):
            original_question = user_input[len("Elaborate on:"):].strip()
        elif user_input_stripped == "elaborate":
            original_question = extra_context.strip() if extra_context else ""
        else:
            original_question = None
        if original_question is not None and original_question:
            retrieved = retrieve(original_question)
            context = build_intelligent_context(retrieved)
            convo_type = analyze_conversation_context(original_question, retrieved)
            prompt = get_dynamic_prompt(convo_type, original_question)
            full_prompt = f"{SYSTEM_PERSONA}\nPlease elaborate in simple language, at least 70 words, about: {original_question}. Do not repeat the previous answer.\n{prompt}\nContext:\n{context}\nUser: {original_question}\nAnswer:"
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": SYSTEM_PERSONA},
                          {"role": "user", "content": full_prompt}],
                max_tokens=350,
                temperature=0.7
            )
            answer = response.choices[0].message.content.strip()
            return {
                'response': answer,
                'show_demo_popup': False,
                'show_options': False
            }
        # Otherwise, use AI to answer
        # Retrieve context
        retrieved = retrieve(user_input)
        context = build_intelligent_context(retrieved)
        convo_type = analyze_conversation_context(user_input, retrieved)
        prompt = get_dynamic_prompt(convo_type, user_input)
        full_prompt = f"{SYSTEM_PERSONA}\n{prompt}\nContext:\n{context}\nUser: {user_input}\nAnswer:"
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": SYSTEM_PERSONA},
                      {"role": "user", "content": full_prompt}],
            max_tokens=150,
            temperature=0.7
        )
        answer = response.choices[0].message.content.strip()
        # Format as list if needed
        answer = format_list_response(answer)
        # Add context-specific links for products and clients
        input_lower = user_input.lower()
        if not wants_demo:
            if 'product' in input_lower or 'products' in input_lower:
                answer += ' <br><br>Get to know our products <a href="https://www.onpalms.com/products/" target="_blank" style="color:#60a5fa; text-decoration:underline;">here</a>.'
            elif 'client' in input_lower or 'clients' in input_lower:
                answer += ' <br><br>Get to know our clients <a href="https://www.onpalms.com/clients/" target="_blank" style="color:#60a5fa; text-decoration:underline;">here</a>.'
            else:
                answer += ' <br><br>You can talk to our team <a href="https://www.onpalms.com/wms/" target="_blank" style="color:#60a5fa; text-decoration:underline;">here</a>.'
        return {
            'response': answer,
            'show_demo_popup': False,
            'show_options': True  # Always show options for first relevant AI answer
        }
    except Exception as e:
        print(f"AI Error: {e}")
        return {
            'response': "I'm experiencing a technical difficulty. Please try again or contact us directly at https://www.onpalms.com/contact/",
            'show_demo_popup': False,
            'show_options': False
        }

def get_dynamic_prompt(convo_type, user_input):
    """Return context-specific instructions"""
    prompts = {
        "pricing_inquiry": """
        This appears to be a pricing inquiry. Be specific about pricing tiers if available, 
        but if exact pricing isn't in context, focus on value proposition and offer to connect with sales.
        """,
        
        "feature_inquiry": """
        This is a feature question. Explain capabilities clearly, provide specific examples from context,
        and connect features to potential business benefits.
        """,
        
        "social_proof": """
        This requests social proof. Share relevant client success stories, case studies, or testimonials.
        Focus on results and measurable outcomes mentioned in context.
        """,
        
        "technical_inquiry": """
        This is a technical question. Provide clear, accurate technical information from context.
        Explain complex concepts in simple terms and mention integration capabilities if relevant.
        """,
        
        "conversion_request": """
        This is a conversion opportunity! Make it easy to take next steps - provide clear contact options,
        demo scheduling information, or specific next actions mentioned in context.
        """,
        
        "general_inquiry": """
        This is a general inquiry. Provide helpful, comprehensive information from context.
        Look for opportunities to educate and identify potential needs for PALMS solutions.
        """
    }
    
    return prompts.get(convo_type, prompts["general_inquiry"])