from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "tutoriais.py"
SPEC = importlib.util.spec_from_file_location("suap_tutoriais", SCRIPT)
assert SPEC and SPEC.loader
tutoriais = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tutoriais)


def sample_categories():
    return [
        {"id": 311, "parent": 0, "name": "SUAP", "slug": "suap"},
        {"id": 110, "parent": 311, "name": "Ensino", "slug": "ensino"},
        {"id": 337, "parent": 110, "name": "Registro Acadêmico", "slug": "registro"},
        {"id": 999, "parent": 0, "name": "Outra raiz", "slug": "outra"},
    ]


def sample_posts():
    return [
        {
            "id": 2,
            "title": {"rendered": "Matrícula de aluno avulso"},
            "slug": "matricula-aluno-avulso",
            "link": "https://ifpr.edu.br/tutoriais/base-conhecimento/matricula-aluno-avulso/",
            "modified": "2026-01-02T10:00:00",
            "epkb_post_type_1_category": [337],
        },
        {
            "id": 1,
            "title": {"rendered": "Atualização de curso"},
            "slug": "atualizacao-curso",
            "link": "https://ifpr.edu.br/tutoriais/base-conhecimento/atualizacao-curso/",
            "modified": "2026-01-01T10:00:00",
            "epkb_post_type_1_category": [110],
        },
    ]


class TutorialIndexTests(unittest.TestCase):
    def test_pagination_collects_every_page(self):
        pages = {
            1: [{"id": value} for value in range(100)],
            2: [{"id": 100}],
        }

        result = tutoriais.fetch_paginated(lambda page, _per_page: pages[page])

        self.assertEqual(101, len(result))
        self.assertEqual(100, result[-1]["id"])

    def test_build_index_filters_tree_and_is_deterministic(self):
        first = tutoriais.build_index(sample_categories(), list(reversed(sample_posts())))
        second = tutoriais.build_index(sample_categories(), sample_posts())

        self.assertEqual(first, second)
        self.assertEqual(3, first["source"]["category_count"])
        self.assertEqual(2, first["source"]["tutorial_count"])
        self.assertEqual("Atualização de curso", first["tutorials"][0]["title"])
        self.assertEqual(
            ["SUAP", "Ensino", "Registro Acadêmico"],
            first["tutorials"][1]["paths"][0],
        )

    def test_search_ignores_accents_and_case(self):
        index = tutoriais.build_index(sample_categories(), sample_posts())

        result = tutoriais.search_tutorials(index, ["MATRICULA", "academico"])

        self.assertEqual([2], [item["id"] for item in result])

    def test_search_ranks_partial_match_when_phrase_is_not_in_metadata(self):
        index = tutoriais.build_index(sample_categories(), sample_posts())

        result = tutoriais.search_tutorials(index, ["matricula", "aluno", "avulso"])

        self.assertEqual(2, result[0]["id"])

    def test_validation_rejects_external_url_and_extra_content(self):
        index = tutoriais.build_index(sample_categories(), sample_posts())
        index["tutorials"][0]["url"] = "https://example.com/tutorial"

        errors = tutoriais.validation_errors(index)

        self.assertTrue(any("URL externa" in error for error in errors))

        index["tutorials"][0]["content"] = "corpo indevido"
        errors = tutoriais.validation_errors(index)
        self.assertTrue(any("estrutura inválida" in error for error in errors))

    def test_config_prefers_process_and_never_prints_values(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env.local"
            env_path.write_text("SUAP_USUARIO=arquivo\nSUAP_SENHA=segredo-arquivo\n", encoding="utf-8")
            resolved = tutoriais.resolve_config(
                env_path,
                {"SUAP_USUARIO": "processo", "SUAP_SENHA": "segredo-processo"},
            )
            self.assertEqual("processo", resolved["SUAP_USUARIO"])

            args = type("Args", (), {"env_file": env_path})()
            output = io.StringIO()
            with redirect_stdout(output):
                tutoriais.command_config(args)

        rendered = output.getvalue()
        self.assertNotIn("arquivo", rendered)
        self.assertNotIn("segredo", rendered)
        self.assertIn("SUAP_USUARIO", rendered)

    def test_config_reports_only_missing_key_name(self):
        with tempfile.TemporaryDirectory() as directory:
            env_path = Path(directory) / ".env.local"
            env_path.write_text("SUAP_USUARIO=usuario-teste\n", encoding="utf-8")

            with self.assertRaises(tutoriais.SkillError) as context:
                tutoriais.require_config(env_path)

        self.assertIn("SUAP_SENHA", str(context.exception))
        self.assertNotIn("usuario-teste", str(context.exception))

    def test_index_does_not_contain_credentials(self):
        index = tutoriais.build_index(sample_categories(), sample_posts())

        errors = tutoriais.validation_errors(index, ["segredo-supersecreto"])

        self.assertEqual([], errors)
        self.assertNotIn("segredo-supersecreto", json.dumps(index))

        index["tutorials"][0]["title"] = "segredo-supersecreto"
        errors = tutoriais.validation_errors(index, ["segredo-supersecreto"])
        self.assertTrue(any("credencial" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
