"""Tests for project persistence (save/load)."""
import json
import pytest
from src.packet_tracer_mcp.infrastructure.persistence.project_repository import ProjectRepository


class TestProjectRepository:
    def test_list_empty(self, tmp_path):
        repo = ProjectRepository(base_dir=str(tmp_path))
        projects = repo.list_projects()
        assert projects == []

    def test_save_and_load(self, basic_plan, tmp_path):
        repo = ProjectRepository(base_dir=str(tmp_path))
        repo.save_plan(basic_plan, project_name="test_proj")
        loaded = repo.load_plan("test_proj")
        assert loaded.name == basic_plan.name
        assert len(loaded.devices) == len(basic_plan.devices)
        assert len(loaded.links) == len(basic_plan.links)

    def test_list_after_save(self, basic_plan, tmp_path):
        repo = ProjectRepository(base_dir=str(tmp_path))
        repo.save_plan(basic_plan, project_name="my_project")
        projects = repo.list_projects()
        names = [p["project_name"] for p in projects]
        assert "my_project" in names

    def test_load_nonexistent_raises(self, tmp_path):
        repo = ProjectRepository(base_dir=str(tmp_path))
        with pytest.raises(FileNotFoundError):
            repo.load_plan("does_not_exist")
