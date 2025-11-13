# 🤖 OpenRouter AI Integration Guide

## Overview

Your LinkedIn Easy Apply Bot now includes OpenRouter AI integration for intelligent, AI-powered features like:
- **Cover Letter Generation** - Automatically generate personalized cover letters
- **Question Answering** - Intelligently answer application questions
- **Job Matching Analysis** - Analyze how well you match a job
- **Resume Optimization** - Get suggestions for improving your resume

## Configuration

The OpenRouter API key is already configured in `config.yaml`:

```yaml
openrouter:
  api_key: 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
  default_model: openai/gpt-3.5-turbo
  enabled: true
```

## Usage Examples

### 1. Generate Cover Letter

```python
from openrouter_client import OpenRouterClient

client = OpenRouterClient()

cover_letter = client.generate_cover_letter(
    job_title="Software Engineer",
    company="Tech Corp",
    job_description="We are looking for a Python developer...",
    resume_summary="5 years of Python experience..."
)

print(cover_letter)
```

### 2. Answer Application Question

```python
answer = client.answer_application_question(
    question="Why are you interested in this position?",
    job_title="Software Engineer",
    company="Tech Corp",
    candidate_background="Experienced Python developer..."
)

print(answer)
```

### 3. Analyze Job Match

```python
analysis = client.analyze_job_match(
    job_description="Full job description text...",
    candidate_skills=["Python", "JavaScript", "AWS"],
    candidate_experience="5 years of software development..."
)

print(f"Match Score: {analysis['match_score']}")
print(f"Strengths: {analysis['strengths']}")
print(f"Recommendation: {analysis['recommendation']}")
```

### 4. Get Resume Improvement Suggestions

```python
suggestions = client.improve_resume_for_job(
    current_resume_text="Your resume content...",
    job_description="Job description...",
    job_title="Software Engineer"
)

print(suggestions)
```

## Available Models

You can use different models by specifying the `model` parameter:

- `openai/gpt-3.5-turbo` (default, cost-effective)
- `openai/gpt-4` (more capable, more expensive)
- `anthropic/claude-3-haiku` (fast and efficient)
- `anthropic/claude-3-sonnet` (balanced)
- `anthropic/claude-3-opus` (most capable)
- `google/gemini-pro` (Google's model)

To see all available models:
```python
client = OpenRouterClient()
models = client.list_models()
for model in models:
    print(model['id'])
```

## Integration with Bot

The OpenRouter client is automatically initialized when you run the bot if `enabled: true` is set in config.

You can access it in your code:
```python
# In protected_linkedin_bot.py or custom code
if self.openrouter:
    answer = self.openrouter.answer_application_question(
        question="...",
        job_title="...",
        company="..."
    )
```

## Cost Considerations

- **GPT-3.5-turbo**: ~$0.0015 per 1K tokens (very affordable)
- **GPT-4**: ~$0.03 per 1K tokens (more expensive)
- **Claude models**: Varies by model

For most use cases, GPT-3.5-turbo is sufficient and cost-effective.

## Best Practices

1. **Cache responses** - Don't regenerate the same cover letter multiple times
2. **Use appropriate models** - Use GPT-3.5 for simple tasks, GPT-4 for complex ones
3. **Set reasonable token limits** - Don't request unnecessarily long responses
4. **Handle errors gracefully** - API calls can fail, have fallbacks

## Troubleshooting

### API Key Not Working
- Verify the key is correct in `config.yaml`
- Check your OpenRouter account balance
- Ensure `enabled: true` is set

### Rate Limits
- OpenRouter has rate limits based on your plan
- If you hit limits, wait a few minutes and try again
- Consider using a cheaper model for bulk operations

### Errors
- Check the console output for specific error messages
- Verify your internet connection
- Ensure the `requests` library is installed: `pip install requests`

## Security Note

⚠️ **Keep your API key secure!** 
- Never commit it to version control
- Don't share it publicly
- Monitor your usage to prevent unexpected charges

