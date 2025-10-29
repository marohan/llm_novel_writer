# coding=utf-8
"""
Novel writing state save/load utility
"""

import os
import json
from dataclasses import asdict
from novel_writer.writer_config import Chapter
from novel_writer.chapter_manager import ChapterManager
from novel_writer.memory_manager import NovelMemoryManager


class StateManager:
    """A class that manages the novel writing status"""

    def __init__(self, state_file: str = "novel_state.json"):
        self.state_file = state_file

    def save_state(self, cm: ChapterManager, mm: NovelMemoryManager) -> bool:
        """Save the current progress as a JSON file."""
        print(f"\n💾 Saving state... ({self.state_file})")
        try:
            state = {
                "chapters": [asdict(ch) for ch in cm.chapters],
                "memory": mm.to_dict()
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            print("✓ Save complete")
            return True
        except Exception as e:
            print(f"  ⚠️ Save failed: {e}")
            return False

    def load_state(self, cm: ChapterManager, mm: NovelMemoryManager) -> bool:
        """Load previous progress from a JSON file."""
        if not os.path.exists(self.state_file):
            return False

        print(f"🔄 Loading previous state from {self.state_file}...")
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                state = json.load(f)

            chapters = [Chapter(**ch_data) for ch_data in state.get("chapters", [])]
            cm.set_chapters(chapters)

            # Exception handling when restoring memory
            memory_data = state.get("memory", {})
            try:
                mm.from_dict(memory_data)
            except Exception as e:
                print(f"⚠️ Error restoring memory: {e}")
                print("   Start with empty memory.")
                self._initialize_empty_memory(mm)

            print(f"✓ {len(chapters)} chapters and memory loading completed.")
            return True
        except Exception as e:
            print(f"⚠️ Failed to load state: {e}. Starting over.")
            return False

    @staticmethod
    def _initialize_empty_memory(mm: NovelMemoryManager):
        """Force initialization of memory properties"""
        if not hasattr(mm, 'character_development'):
            mm.character_development = {}
        if not hasattr(mm, 'plot_threads'):
            mm.plot_threads = {}
        if not hasattr(mm, 'world_events'):
            mm.world_events = []
        if not hasattr(mm, 'memory'):
            mm.memory = []