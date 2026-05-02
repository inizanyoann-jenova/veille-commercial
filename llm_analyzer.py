import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


SYSTEM_PROMPT = """Tu es un expert en marchés publics spécialisé dans les systèmes \
de sécurité incendie (SSI/CMSI), la vidéosurveillance et les courants faibles. \
Tu analyses des appels d'offres pour DEF Océan Indien, entreprise opérant à \
La Réunion (974) et Mayotte (976).

Réponds UNIQUEMENT en JSON valide avec exactement cette structure :
{
    "type_marche": "Travaux" ou "Maintenance",
    "marques_concurrentes_citees": ["liste", "des", "marques"],
    "risques_penalites": "description courte ou null",
    "score_pertinence": 0
}
Le champ score_pertinence est un entier entre 0 et 100 indiquant l'adéquation \
avec le cœur de métier de DEF (SSI, détection incendie, vidéosurveillance)."""


def analyze_tender(text: str) -> dict:
    try:
        response = _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Analyse ce marché public :\n\n{text[:3000]}",
                },
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        return json.loads(response.choices[0].message.content)

    except Exception as exc:
        return {
            "type_marche": "Inconnu",
            "marques_concurrentes_citees": [],
            "risques_penalites": None,
            "score_pertinence": 0,
            "error": str(exc),
        }
