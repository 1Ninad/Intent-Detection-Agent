from rapidfuzz import fuzz, process
import tldextract
import re


class EntityResolver:
    def __init__(self, tech_dictionary=None, fuzz_threshold=75):
        """
        :param tech_dictionary: list or set of canonical technology names
        :param fuzz_threshold: similarity threshold for fuzzy matching
        """
        default_dictionary = {
            # Databases
            "Neo4j", "Qdrant", "PostgreSQL", "MongoDB", "MySQL", "Redis", "Elasticsearch",
            # Frameworks / APIs
            "LangChain", "FastAPI", "Flask", "Django", "Spring Boot",
            # ML / AI
            "TensorFlow", "PyTorch", "scikit-learn", "Hugging Face",
            "OpenAI", "Transformers",
            # Cloud / DevOps
            "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Terraform",
            # Data
            "Pandas", "NumPy", "Apache Spark", "Hadoop", "Kafka",
            # Frontend / UI
            "React", "Angular", "Vue.js", "Streamlit"
        }

        # Use provided dictionary OR fallback to default
        self.tech_dictionary = set(tech_dictionary) if tech_dictionary else default_dictionary
        self.fuzz_threshold = fuzz_threshold

    # --- Company Resolution ---
    def normalize_company(self, name: str) -> str:
        """Normalize company names (strip Inc., Ltd., punctuation)."""
        if not name:
            return None
        name = name.lower()
        name = re.sub(r"\b(inc|ltd|llc|corp|co)\b\.?", "", name)
        name = re.sub(r"[^a-z0-9 ]", "", name)
        return name.strip()

    def extract_domain(self, url: str) -> str:
        """Extract clean domain name from URL."""
        if not url:
            return None
        ext = tldextract.extract(url)
        return f"{ext.domain}.{ext.suffix}" if ext.domain and ext.suffix else None

    # --- Executive Resolution ---
    def normalize_person(self, name: str) -> str:
        """Normalize person names to consistent form."""
        if not name:
            return None
        return " ".join([part.capitalize() for part in name.strip().split()])

    # --- Technology Resolution ---
    def resolve_technology(self, tech: str) -> str:
        """Fuzzy match tech terms to canonical dictionary."""
        if not tech or not self.tech_dictionary:
            return tech

        match, score, _ = process.extractOne(
            tech, self.tech_dictionary, scorer=fuzz.token_sort_ratio
        )
        return match if score >= self.fuzz_threshold else tech
