from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import json
from groq import Groq
from datetime import datetime
import re

class TemplateManager:
    def __init__(self, db_session, groq_client):
        self.db = db_session
        self.groq_client = groq_client
        self.placeholder_pattern = re.compile(r'\{([^}]+)\}')

    async def analyze_template(self, content: str) -> Dict:
        """Analyze template for quality and extract placeholders"""
        placeholders = set(self.placeholder_pattern.findall(content))
        
        # Use Groq to analyze template quality
        analysis_prompt = f"""
        Analyze this email template for quality and provide scores for:
        1. Professionalism (1-10)
        2. Clarity (1-10)
        3. Engagement potential (1-10)
        4. Spam risk (1-10)

        Template:
        {content}

        Provide the analysis in JSON format.
        """

        response = await self.groq_client.chat.completions.create(
            messages=[{"role": "user", "content": analysis_prompt}],
            model="mixtral-8x7b-32768",
            temperature=0.7
        )

        try:
            quality_scores = json.loads(response.choices[0].message.content)
        except json.JSONDecodeError:
            quality_scores = {
                "professionalism": 0,
                "clarity": 0,
                "engagement": 0,
                "spam_risk": 0
            }

        return {
            "placeholders": list(placeholders),
            "quality_scores": quality_scores,
            "word_count": len(content.split()),
            "estimated_read_time": len(content.split()) // 200  # minutes
        }

    async def create_template(self, template: Dict) -> Dict:
        """Create a new email template with AI-powered suggestions"""
        # Analyze template
        analysis = await self.analyze_template(template["content"])
        
        # Generate subject line suggestions
        subject_suggestions = await self.generate_subject_lines(template["content"])
        
        # Store template with metadata
        template_data = {
            **template,
            "analysis": analysis,
            "subject_suggestions": subject_suggestions,
            "created_at": datetime.now(),
            "version": 1
        }
        
        result = await self.db.email_templates.insert_one(template_data)
        return {"id": str(result.inserted_id), **template_data}

    async def generate_subject_lines(self, content: str) -> List[str]:
        """Generate AI-powered subject line suggestions"""
        prompt = f"""
        Based on this email content, generate 5 engaging subject lines that:
        - Are attention-grabbing but professional
        - Avoid spam trigger words
        - Are 30-60 characters long
        - Have high open rate potential

        Email content:
        {content}

        Provide only the subject lines, one per line.
        """

        response = await self.groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="mixtral-8x7b-32768",
            temperature=0.8
        )

        subject_lines = response.choices[0].message.content.strip().split('\n')
        return subject_lines[:5]

    async def optimize_template(self, template_id: str) -> Dict:
        """Optimize existing template for better performance"""
        template = await self.db.email_templates.find_one({"_id": template_id})
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        optimization_prompt = f"""
        Optimize this email template for better engagement while maintaining the same message:
        1. Improve readability
        2. Add persuasive elements
        3. Optimize for mobile viewing
        4. Maintain professional tone
        5. Keep all existing placeholders

        Original template:
        {template['content']}

        Provide only the optimized template.
        """

        response = await self.groq_client.chat.completions.create(
            messages=[{"role": "user", "content": optimization_prompt}],
            model="mixtral-8x7b-32768",
            temperature=0.7
        )

        optimized_content = response.choices[0].message.content.strip()
        
        # Analyze optimized version
        analysis = await self.analyze_template(optimized_content)
        
        # Store new version
        template["content"] = optimized_content
        template["version"] += 1
        template["analysis"] = analysis
        template["optimized_at"] = datetime.now()
        
        await self.db.email_templates.replace_one(
            {"_id": template_id},
            template
        )
        
        return template

    async def generate_variations(self, template_id: str, count: int = 3) -> List[Dict]:
        """Generate A/B testing variations of a template"""
        template = await self.db.email_templates.find_one({"_id": template_id})
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        variation_prompt = f"""
        Create {count} variations of this email template:
        1. Keep the same message and placeholders
        2. Vary tone and structure
        3. Each variation should be unique but professional
        4. Maintain all existing placeholders: {', '.join(template['analysis']['placeholders'])}

        Original template:
        {template['content']}

        Provide {count} variations, separated by '---'.
        """

        response = await self.groq_client.chat.completions.create(
            messages=[{"role": "user", "content": variation_prompt}],
            model="mixtral-8x7b-32768",
            temperature=0.9
        )

        variations = response.choices[0].message.content.split('---')
        
        variation_results = []
        for idx, content in enumerate(variations[:count]):
            analysis = await self.analyze_template(content.strip())
            variation = {
                "parent_id": template_id,
                "content": content.strip(),
                "analysis": analysis,
                "variation_number": idx + 1,
                "created_at": datetime.now()
            }
            variation_results.append(variation)
        
        return variation_results