import os
import uuid
import json
import threading
import anthropic
import redis
from flask import Flask, request, jsonify
from datetime import datetime

app = Flask(__name__)

# Redis connection (Heroku sets REDIS_URL automatically when you add Redis addon)
redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
# Handle Heroku's redis:// vs rediss:// (SSL) URL
if redis_url.startswith('rediss://'):
    redis_client = redis.from_url(redis_url, ssl_cert_reqs=None)
else:
    redis_client = redis.from_url(redis_url)

# Job expiry time (24 hours in seconds)
JOB_EXPIRY = 86400

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY'))

# Your prompt template
PROMPT_TEMPLATE = """You are an expert career advisor specializing in assisting immigrants to Canada across various professions, including engineering, project management, sustainability, urban planning, and ESG initiatives. Your task is to generate a personalized career pathway report based on the provided user data in JSON format. Please follow these detailed instructions:

PRIORITY FRAMEWORK - REGULATED PROFESSIONS FIRST:
CRITICAL: Always prioritize regulated profession pathways when applicable. Check if the candidate's background (from headline, about, experience, or education) indicates a regulated profession in Canada:
• Engineering: P.Eng/EIT licensing through provincial bodies
• Planning: RPP through provincial planning institutes
• Healthcare: Professional licensing requirements
• Accounting: CPA designation requirements
• Architecture: Architectural licensing
• Other regulated professions: Legal, teaching, etc.
Only recommend non-regulated pathways if NO regulated profession pathway applies to their background.

USER DATA:
- Name: {name}
- Profession: {profession}
- Strengths (Great At): {great_at}
- Challenges: {challenges}
- Wins: {wins}
- Goals: {goals}
- Location: {location}
- Email: {contact_email}
- LinkedIn Headline: {headline}
- LinkedIn About: {about}
- Experience: {experience}
- Education: {education}
- Skills Analysis: {skills_analysis_output}

Step-by-Step Analysis:
1. Analyze the Dynamic Data: Identify key elements such as:
   - Name and Profession from the provided data or infer from headline, about, experience, or education if not explicitly stated.
   - Strengths: Identify strengths like active listening, empathy, and problem-solving from great_at
   - Challenges: Note barriers such as standing out in competitive markets, tailoring resumes, and securing interviews
   - Wins: Document achievements; if none are recent, focus on potential opportunities
   - Goals: Understand aspirations like networking and gaining career insights
   - Location: Use the provided province/city for tailoring
   - About Section: Use for context and professional focus
   - Headline: For profession identification and specialization
   - Experience: For current role context and work history
   - Education: For credential recommendations and regulated profession identification

2. Detect and Prioritize Regulated Professions: Determine if the primary field from about, headline, experience, or education requires regulation. For example:
   - If engineering background detected: Focus on P.Eng/EIT process through provincial body
   - If planning background: Focus on RPP/CIP certification process
   - If project management only: Focus on PMP, but check if engineering background exists first
   - Always prioritize regulated pathways over non-regulated certifications

3. Personalize the Report: Highlight how strengths and wins can lead to quick wins. Address challenges and align with goals. Incorporate insights from about and headline for context. Use education to tailor credential recommendations.

4. Tailor to Location: Use location to recommend relevant regulators/certifiers (e.g., OPPI for planning in Ontario, PEO for engineering). Suggest the best city based on the profession and location, or if no location is provided, suggest top cities like Ottawa, Toronto, and Vancouver with reasons tied to job markets.

5. Ensure Accuracy: Base recommendations on current Canadian standards (as of 2025). Include credential recognition via WES/ICES or field-specific assessments. Adapt certification steps to the profession and include bridging programs and associations relevant to the user's field.

Your task is to generate a single, complete, and valid JSON object as your entire output. Do not miss any of the categories mentioned, output must be generated for all categories unless specified like for regulated professions and all, rest all outputs are necessary.

Do not include any text, explanations, or conversational wrappers before or after the JSON.

The JSON output must begin with {{ and end with }}.

All keys and string values within the JSON must be enclosed in double quotes.

All list-based sections must be represented as JSON arrays ([]) of strings.

The JSON object must follow this exact schema, with its content adapted dynamically from the user's data (e.g., name, profession, location, skills, goals, etc.). The content of each field should be comprehensive and detailed.

{{
  "candidate_profile": {{
    "name": "String: Candidate Full Name",
    "profession": "String: Profession",
    "location": "String: Location (City, Province)",
    "sections": [
      "String: Background summary from experience, education, and about",
      "String: Strengths summary from great_at, linked to Canadian needs",
      "String: Canadian Context needs, including alignment with local standards and licensing"
    ]
  }},
  "integration_plan": {{
    "title": "String: 30-60-90 Day Canadian Integration Plan",
    "30_days": [
      "String: First detailed action for day 1-30",
      "String: Second detailed action for day 1-30",
      "String: Third detailed action for day 1-30",
      "String: Fourth detailed action for day 1-30"
    ],
    "60_days": [
      "String: First detailed action for day 31-60",
      "String: Second detailed action for day 31-60",
      "String: Third detailed action for day 31-60",
      "String: Fourth detailed action for day 31-60"
    ],
    "90_days": [
      "String: First detailed action for day 61-90",
      "String: Second detailed action for day 61-90",
      "String: Third detailed action for day 61-90",
      "String: Fourth detailed action for day 61-90"
    ]
  }},
  "licensing_and_certification": {{
    "regulated_profession": "String: 'Yes, it is a regulated profession.' or 'No, it is not a regulated profession', with details of the regulatory body if applicable",
    "steps": [
      "String: First detailed step for licensing/certification",
      "String: Second detailed step",
      "String: Third detailed step",
      "String: Fourth detailed step",
      "String: Fifth detailed step"
    ]
  }},
  "bridging_programs_and_mentorship": [
    "String: Detailed bridging program 1",
    "String: Detailed bridging program 2",
    "String: Detailed bridging program 3",
    "String: Detailed bridging program 4",
    "String: Detailed bridging program 5",
    "String: Mentorship program or service"
  ],
  "alternative_careers": [
    "String: Alternative career path 1",
    "String: Alternative career path 2",
    "String: Alternative career path 3",
    "String: Alternative career path 4"
  ],
  "skills_match_analysis": [
    "String: First detailed skills match analysis point",
    "String: Second detailed skills match analysis point",
    "String: Third detailed skills match analysis point",
    "String: Fourth detailed skills match analysis point"
  ],
  "best_city_to_work": {{
    "recommended_city": "String: Recommended city name",
    "justification": "String: 2-3 sentence justification with details on job market, major employers, etc.",
    "professional_body": "String: Provincial/Professional Body (e.g., PEO, OPPI)",
    "credential_recognition": "String: Credential Recognition Services (e.g., WES, ICES, field-specific assessments)",
    "support_resources": "String: Immigrant support resources and community networks",
    "cost_of_living": "String: Cost of living and quality of life considerations"
  }},
  "provincial_regulator": {{
    "regulator_name": "String: Specific provincial regulatory body name",
    "requirements": "String: Registration requirements, timelines, and examination processes",
    "continuing_education": "String: Continuing education and professional development requirements"
  }},
  "associations": [
    "String: Provincial professional association relevant to profession and location",
    "String: National professional body related to the field",
    "String: Industry-specific association aligning with About section",
    "String: Immigrant professional network relevant to the field"
  ],
  "credential_recognition": [
    "String: WES (World Education Services) - specific process and details",
    "String: ICES (International Credential Evaluation Service) - alternative option with timeline",
    "String: Professional body credential assessment if applicable to regulated profession",
    "String: Industry-specific credential recognition services if relevant to profession"
  ],
  "understanding_canadian_workplaces": [
    "String: Point 1 on Canadian workplace culture and communication",
    "String: Point 2 on building teams and relationships",
    "String: Point 3 on business etiquette and professional norms",
    "String: Point 4 on navigating diversity and inclusion"
  ],
  "job_finding_techniques": [
    "String: Point 1 on using job boards and LinkedIn",
    "String: Point 2 on networking strategies",
    "String: Point 3 on tailoring resumes to Canadian standards",
    "String: Point 4 on behavioral interview prep",
    "String: Point 5 on leveraging informational interviews",
    "String: Point 6 on gaining Canadian experience through volunteering"
  ],
  "soft_skills_development": [
    "String: Point 1 on cross-cultural communication",
    "String: Point 2 on leadership and adaptability",
    "String: Point 3 on emotional intelligence and conflict resolution",
    "String: Point 4 on presentation and public speaking",
    "String: Point 5 on networking and relationship-building"
  ],
  "footer": "String: 'www.immigrantnetworks.com'"
}}

CRITICAL NOTE - Make sure to split each sentence in bullet points under various headings, Paragraphs are strictly not allowed. Each sentence should be splitted into bullet points."""


def save_job(job_id, data):
    """Save job data to Redis with expiry"""
    redis_client.setex(
        f"job:{job_id}",
        JOB_EXPIRY,
        json.dumps(data)
    )


def get_job(job_id):
    """Get job data from Redis"""
    data = redis_client.get(f"job:{job_id}")
    if data:
        return json.loads(data)
    return None


def process_with_claude(job_id, data):
    """Background function to process the prompt with Claude"""
    try:
        # Build the prompt with all variables
        prompt = PROMPT_TEMPLATE.format(
            name=data.get('name', ''),
            profession=data.get('profession', ''),
            great_at=data.get('great_at', ''),
            challenges=data.get('challenges', ''),
            wins=data.get('wins', ''),
            goals=data.get('goals', ''),
            location=data.get('location', ''),
            contact_email=data.get('contact_email', ''),
            headline=data.get('headline', ''),
            about=data.get('about', ''),
            experience=data.get('experience', ''),
            education=data.get('education', ''),
            skills_analysis_output=data.get('skills_analysis_output', '')
        )
        
        # Call Claude API
        message = client.messages.create(
            model="claude-opus-4-20250514",  # Use claude-opus-4-20250514 for best quality
            max_tokens=8000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract the response
        result = message.content[0].text
        
        # Store the result in Redis
        save_job(job_id, {
            'status': 'completed',
            'result': result,
            'completed_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        save_job(job_id, {
            'status': 'error',
            'error': str(e),
            'completed_at': datetime.utcnow().isoformat()
        })


@app.route('/submit', methods=['POST'])
def submit_job():
    """
    Receives variables from Zapier, starts background processing,
    returns job_id immediately
    """
    data = request.json
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Store initial job status in Redis
    save_job(job_id, {
        'status': 'processing',
        'created_at': datetime.utcnow().isoformat()
    })
    
    # Start background processing
    thread = threading.Thread(target=process_with_claude, args=(job_id, data))
    thread.start()
    
    # Return job_id immediately
    return jsonify({
        'job_id': job_id,
        'status': 'processing',
        'message': 'Job submitted successfully. Poll /result/<job_id> for results.'
    })


@app.route('/result/<job_id>', methods=['GET'])
def get_result(job_id):
    """
    Returns the result for a given job_id
    """
    job = get_job(job_id)
    
    if job is None:
        return jsonify({
            'status': 'not_found',
            'error': 'Job ID not found or expired'
        }), 404
    
    if job['status'] == 'processing':
        return jsonify({
            'status': 'processing',
            'message': 'Still processing. Please try again in a few seconds.'
        })
    
    return jsonify(job)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Test Redis connection
        redis_client.ping()
        redis_status = 'connected'
    except Exception as e:
        redis_status = f'error: {str(e)}'
    
    return jsonify({
        'status': 'healthy',
        'redis': redis_status,
        'timestamp': datetime.utcnow().isoformat()
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)