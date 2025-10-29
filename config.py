# coding=utf-8
"""
Novel writing system settings file
"""

import os
from typing import Tuple
from novel_writer.writer_config import NovelSetup, WriterConfig


def setup_novel() -> Tuple[NovelSetup, WriterConfig]:
    """Defines the novel and its author settings"""

    # 소설의 기본 설정
    setup = NovelSetup(
        synopsis=(
            "Tutu, a stuffed rabbit, falls from its owner Sodam's picnic bag and becomes alone."
            "Left alone in the forest, Tutu becomes anxious, separated from his owner for the first time in his life."
            "Tutu wanders through the forest and meets the friendly snail Slowy."
            "Slowy hears Tutu's story and asks his forest friends for help."
            "While heading to the village with the butterfly Fluttery, who knows the way, they encounter sudden rain."
            "Tutu is in danger of falling into the mud."
            "Thanks to the resourcefulness and cooperation of a group of ants and the squirrel Coco, Tutu escapes the rain."
            "They succeed in moving to the village."
            "With the help of his friends, Tutu arrives near his home. She cries and searches for Tutu."
            "Sodam finds him and gives him a warm hug."
            "Tutu whispers thanks to his friends and returns to Sodam's embrace."
        ),

        writing_style=(
            "Use short, concise, and warm sentences."
            "Use onomatopoeia and mimetic words appropriately to create a sense of liveliness and emphasize clear and pure images."
            "Delicately depict the protagonist Tutu's anxiety and earnestness, and the helpers' kindness and energy."
            "Metaphorical expressions (e.g., Tutu's soft heart, like her fur; her cautious steps, like the slow pace of time)."
            "Intended for preschoolers and early elementary school students, convey a hopeful and warm feeling."
            "Shows that conflicts are not serious, and difficulties are always resolved through the goodwill and cooperation of young friends."
            "A reassuring tone. (e.g., insert repetitive, warm dialogue like, 'It's okay, don't worry.')"
        ),

        style_example="Slowy the snail asked slowly and steadily. Tutu nodded without saying a word.",

        characters=[
            {
                "name": "Tutu",
                "description": (
                    "The main character. A cute, white-furred rabbit doll. Deeply loved by its owner, Sodam."
                    "It has fluffy fur and button eyes, so its expression remains unchanged, but."
                    "It has a warm heart and a great sense of anxiety."
                    "It can't move on its own, but it senses the slightest sounds and actions around it and never loses hope."
                )
            },
            {
                "name": "Sodam",
                "description": (
                    "A seven-year-old girl. Her owner cherishes and loves Tutu the most."
                    "After losing Tutu, she became anxious and searched diligently for the area where it fell."
                )
            },
            {
                "name": "Slowy",
                "description": (
                    "Helper 1. A snail with a shiny shell on its back."
                    "Slow, but very careful and wise."
                    "He becomes Tutu's first advisor and helps gather his friends."
                )
            },
            {
                "name": "Fluttery",
                "description": (
                    "Helper 2. A butterfly with gorgeous wings."
                    "Having flown across the vast world, she's well-versed in geography."
                    "Helping Tutu on his journey with speed, she's vulnerable to unpredictable weather."
                )
            },
            {
                "name": "the Ants",
                "description": (
                    "Helper 3. A small but strong ant colony."
                    "They provide the practical 'force' to carry the endangered Tutu to safety."
                )
            },
            {
                "name": "Coco",
                "description": (
                    "Helper 4. A lively and clever squirrel."
                    "He makes good use of the surrounding terrain."
                    "He provides crucial assistance in solving problems with quick and ingenious ideas in emergency situations."
                )
            },
        ],

        world_setting=(
            "The 'forest' is located directly adjacent to human living spaces (parks, playgrounds, and near homes)."
            "The forest is brightly lit and flowers bloom during the day, but to the doll, it feels like a place full of unknown adventures."
            "The doll (Tutu) cannot move or speak on her own, but,"
            "she feels all emotions and understands the speech of her animal/insect friends."
            "The animals and insect friends communicate in their own way, invisible to humans."
            "She regards the doll as a 'special guest who cannot move,' and is not afraid to help."
            "A 'day's adventure' where all events are resolved before sunset (a short afternoon)."
            "The events unfold over a short period of time, but to Tutu, it feels like a long and arduous journey."
        ),

        target_chapters=5,
        target_words_per_chapter=300,
        words_tolerance=0.5,
        short_term_memory_chapters=3,
        short_term_memory_max_chars=3000,
        enable_ltm_optimization=True
    )

    # Writer API Configuration
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("❌ GEMINI_API_KEY Environment variable not set.")

    # api_key = os.environ.get("GROQ_API_KEY")
    # if not api_key:
    #     raise ValueError("❌ GROQ_API_KEY Environment variable not set.")


    config = WriterConfig(
        api_key=api_key,
        writer_model="gemini-2.5-flash-lite",
        editor_model="gemini-2.5-flash-lite",
        embedding_model="gemini-embedding-001",
        max_generation_tokens=8000,
        max_review_tokens=6000,
        rate_limit_delay=10.0,
        auto_save_interval=1,
        recent_context_chapters=2,
        max_refinement_rounds=2,
        approval_score_threshold=7.0,
        max_retries=10,
        retry_delay=30.0,
        rate_limit_max_retries=10,

        # Long-term Memory Optimization Configuration
        ltm_optimization_interval=3,
        ltm_max_character_events=15,
        ltm_max_plot_threads=20,
        ltm_optimizer_temperature=0.3
    )

    return setup, config