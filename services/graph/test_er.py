import unittest
from er import EntityResolver


class TestEntityResolver(unittest.TestCase):
    def setUp(self):
        techs = {"Neo4j", "Qdrant", "PostgreSQL", "MongoDB", "MySQL", "Redis", "Elasticsearch",
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
                "React", "Angular", "Vue.js", "Streamlit"}
        self.er = EntityResolver(tech_dictionary=techs)

    # --- Company Tests ---
    def test_normalize_company_basic(self):
        self.assertEqual(self.er.normalize_company("TestCorp Inc."), "testcorp")

    def test_normalize_company_with_symbols(self):
        self.assertEqual(self.er.normalize_company("Data-Systems LLC"), "datasystems")

    def test_normalize_company_empty(self):
        self.assertIsNone(self.er.normalize_company(""))

    def test_normalize_company_none(self):
        self.assertIsNone(self.er.normalize_company(None))

    # --- Domain Tests ---
    def test_extract_domain_https(self):
        self.assertEqual(
            self.er.extract_domain("https://www.testcorp.com/about"),
            "testcorp.com"
        )

    def test_extract_domain_http(self):
        self.assertEqual(
            self.er.extract_domain("http://sub.domain.co.uk/path"),
            "domain.co.uk"
        )

    def test_extract_domain_invalid(self):
        self.assertIsNone(self.er.extract_domain("not a url"))

    def test_extract_domain_none(self):
        self.assertIsNone(self.er.extract_domain(None))

    # --- Executive Tests ---
    def test_normalize_person_basic(self):
        self.assertEqual(self.er.normalize_person("jAnE DOE"), "Jane Doe")

    def test_normalize_person_with_middle(self):
        self.assertEqual(self.er.normalize_person("john michael smith"), "John Michael Smith")

    def test_normalize_person_empty(self):
        self.assertIsNone(self.er.normalize_person(""))

    def test_normalize_person_none(self):
        self.assertIsNone(self.er.normalize_person(None))

    # --- Technology Tests ---
    def test_resolve_technology_exact(self):
        self.assertEqual(self.er.resolve_technology("Neo4j"), "Neo4j")

    def test_resolve_technology_fuzzy(self):
        self.assertEqual(self.er.resolve_technology("Langhain"), "LangChain")

    def test_resolve_technology_low_score(self):
        self.assertEqual(self.er.resolve_technology("CompletelyUnknownTech"), "CompletelyUnknownTech")

    def test_resolve_technology_none(self):
        self.assertIsNone(self.er.resolve_technology(None))

    # --- New Expanded Dictionary Tests ---
    def test_resolve_postgres(self):
        self.assertEqual(self.er.resolve_technology("Postgres"), "PostgreSQL")

    def test_resolve_numpy(self):
        self.assertEqual(self.er.resolve_technology("Numpy"), "NumPy")

    def test_resolve_torch(self):
        self.assertEqual(self.er.resolve_technology("Torch"), "PyTorch")

    def test_resolve_k8s(self):
        self.assertEqual(self.er.resolve_technology("Kubers"), "Kubernetes")


if __name__ == "__main__":
    unittest.main()
