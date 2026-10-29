"""Optional real AI transports. No credentials or raw file contents go to clients."""
import json
import os
import urllib.error
import urllib.request


class ProviderError(Exception):
    pass


def configuration():
    provider = os.getenv('AEGIS_AI_PROVIDER', 'disabled')
    model = os.getenv('AEGIS_AI_MODEL', '')
    ready = bool(model) and (provider == 'bedrock' or (
        provider == 'anthropic' and bool(os.getenv('ANTHROPIC_API_KEY'))))
    return {'provider': provider, 'model': model, 'configured': ready}


def explain(findings):
    config = configuration()
    if not config['configured']:
        raise ProviderError('Configure AEGIS_AI_PROVIDER, AEGIS_AI_MODEL and provider credentials on the server.')
    # File names and source text are untrusted and unnecessary for the model.
    # Only fixed rule metadata produced by our own scanner is transmitted.
    context = [{k: f[k] for k in ('rule', 'severity', 'title', 'remediation')} for f in findings[:50]]
    system = ('You are a DevSecOps reviewer. Explain the supplied policy findings, prioritize fixes, '
              'and describe verification steps. The checks are heuristic, not a security certification. '
              'Do not claim infrastructure was inspected or changed. Do not provide shell commands. '
              'Keep the response under 600 words. Your output is advisory and cannot execute actions.')
    prompt = json.dumps({'policy_findings': context})
    try:
        if config['provider'] == 'anthropic':
            body = {'model': config['model'], 'max_tokens': 1200, 'system': system,
                    'messages': [{'role': 'user', 'content': prompt}]}
            request = urllib.request.Request('https://api.anthropic.com/v1/messages',
                data=json.dumps(body).encode(), headers={'Content-Type': 'application/json',
                'x-api-key': os.environ['ANTHROPIC_API_KEY'], 'anthropic-version': '2023-06-01'})
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.loads(response.read(262144))
            text = '\n'.join(x['text'] for x in result.get('content', []) if x.get('type') == 'text')
        else:
            try:
                import boto3
                from botocore.config import Config
            except ImportError as exc:
                raise ProviderError('Install backend/requirements-ai.txt for Amazon Bedrock.') from exc
            client = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION', 'us-east-1'),
                                  config=Config(connect_timeout=5, read_timeout=45, retries={'max_attempts': 1}))
            result = client.converse(modelId=config['model'], system=[{'text': system}],
                messages=[{'role': 'user', 'content': [{'text': prompt}]}], inferenceConfig={'maxTokens': 1200})
            text = '\n'.join(x['text'] for x in result['output']['message']['content'] if 'text' in x)
        if not text.strip():
            raise ProviderError('AI provider returned no text. Try a supported text model.')
        return {'provider': config['provider'], 'model': config['model'], 'text': text[:16000], 'advisory': True}
    except ProviderError:
        raise
    except Exception as exc:
        # Never expose response bodies, authorization headers or credential errors.
        raise ProviderError('AI request failed. Check server-side provider credentials, model access, region and connectivity.') from exc
