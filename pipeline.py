# coding=utf-8
"""
Novel writing pipeline execution logic
"""

from novel_writer.client_setup import GeminiClient
from novel_writer.writer_config import NovelSetup, WriterConfig
from novel_writer.memory_manager import NovelMemoryManager, LongTermMemoryOptimizer
from novel_writer.chapter_manager import ChapterManager
from novel_writer.writer import Writer
from novel_writer.editor import Editor
from novel_writer.summarizer import Summarizer
from novel_writer.structure_generator import StructureGenerator
from novel_writer.utils import count_words

from state_utils import StateManager
from memory_utils import extract_long_term_memory, format_long_term_memory_for_prompt


class NovelPipeline:
    """A class that manages the novel writing pipeline"""

    def __init__(self, setup: NovelSetup, config: WriterConfig,
                 state_file: str = "novel_state.json",
                 output_file: str = "final_novel.txt"):
        self.setup = setup
        self.config = config
        self.state_manager = StateManager(state_file)
        self.output_file = output_file

        # Initializing API clients and tools
        self.client = GeminiClient(config)
        self.writer = Writer(self.client, config, setup)
        self.editor = Editor(self.client, config, setup)
        self.summarizer = Summarizer(self.client, config)
        self.struct_gen = StructureGenerator(self.client, config, setup)
        self.ltm_optimizer = LongTermMemoryOptimizer(self.client, config, setup)

        # Initialize chapter and memory manager
        try:
            self.chapter_manager = ChapterManager()
        except TypeError:
            self.chapter_manager = ChapterManager(setup.characters)

        self.memory_manager = NovelMemoryManager(setup.characters)

    def run(self):
        """Running the main pipeline"""
        print("=" * 60)
        print("🤖 Novel Auto-Writing System v0.1.0 (Long-term Memory Optimization Added)")
        print("=" * 60)

        try:
            # Load state (continue to write)
            self.state_manager.load_state(self.chapter_manager, self.memory_manager)

            # Creating a chapter structure (when first starting out)
            if not self.chapter_manager.chapters:
                self._generate_structure()

            # Write chapters sequentially
            self._write_chapters()

            # Generate final results
            self._save_final_novel()

        except KeyboardInterrupt:
            self._handle_interruption()
        except Exception as e:
            self._handle_error(e)

    def _generate_structure(self):
        """Create a chapter structure"""
        print("\n" + "=" * 60)
        print("📝 Step 1: Create a chapter structure")
        print("=" * 60)

        chapters = self.struct_gen.generate()

        # 구조 검토 (선택적)
        review = self.editor.review_structure(chapters)
        if review['status'] != 'Approved' and review['feedback_text']:
            print(f"\n🔄 Structural modifications are needed")
            print(f"Feedback: {review['feedback_text'][:200]}...")
            chapters = self.writer.refine_structure(chapters, review)

        self.chapter_manager.set_chapters(chapters)
        self.state_manager.save_state(self.chapter_manager, self.memory_manager)
        print("\n✓ The chapter structure has been finalized.")

    def _write_chapters(self):
        """Write chapters sequentially"""
        total_chapters = len(self.chapter_manager.chapters)
        print("\n" + "=" * 60)
        print(f"✍️ Step 2: Start writing {total_chapters} chapters")
        if self.setup.enable_ltm_optimization:
            print(f"🧠 Long-term memory optimization: Activate for each {self.config.ltm_optimization_interval} chapter(s)")
        print("=" * 60)

        for i in range(1, total_chapters + 1):
            current_chapter = self.chapter_manager.get_chapter(i)

            # Processing already written chapters
            if current_chapter.content:
                self._handle_completed_chapter(i, current_chapter)
                continue

            # Write a new chapter
            self._write_single_chapter(i, current_chapter)

    def _handle_completed_chapter(self, chapter_num: int, chapter):
        """Processing already written chapters"""
        print(f"\n⏭️ Skip Chapter {chapter_num}/{len(self.chapter_manager.chapters)} (already written)")

        # Optimization check for completed chapters
        if self.ltm_optimizer.should_optimize(chapter_num):
            self._optimize_memory(chapter_num)

    def _write_single_chapter(self, chapter_num: int, chapter):
        """Write a single chapter"""
        print("\n" + "-" * 60)
        print(f"📖 Chapter {chapter_num}/{len(self.chapter_manager.chapters)}: '{chapter.title}'")
        print("-" * 60)

        # Context preparation
        context = self._prepare_context(chapter)
        short_term_memory = self._prepare_short_term_memory(chapter.number)
        long_term_memory = self._prepare_long_term_memory()

        # Next Chapter Overview
        next_chapter = self.chapter_manager.get_chapter(chapter_num + 1)
        next_outline = next_chapter.outline if next_chapter else None

        # Target words amount
        target_words = self._calculate_target_words()

        # Write-Review-Revise Cycle
        self._write_and_refine_chapter(
            chapter, context, target_words,
            short_term_memory, long_term_memory, next_outline
        )

        # Summary and memory update
        self._summarize_and_update_memory(chapter)

        # Autosave
        if chapter.number % self.config.auto_save_interval == 0:
            self.state_manager.save_state(self.chapter_manager, self.memory_manager)

        # Long-term memory optimization
        if self.ltm_optimizer.should_optimize(chapter_num):
            self._optimize_memory(chapter_num)

    def _prepare_context(self, chapter) -> str:
        """Context preparation"""
        try:
            memory_summary = self.memory_manager.get_summary(self.config.memory_max_length)
            global_outline = self.chapter_manager.get_global_outline_context(chapter.number)
            context = self.chapter_manager.build_context(
                current_number=chapter.number,
                recent_count=self.config.recent_context_chapters,
                memory_summary=memory_summary,
                global_outline_context=global_outline
            )
        except Exception as e:
            print(f"⚠️ Error preparing context: {e}")
            context = f"Chapter {chapter.number}: {chapter.title}\n{chapter.outline}"
        return context

    def _prepare_short_term_memory(self, chapter_num: int) -> str:
        """Short-term memory preparation"""
        try:
            stm = self.chapter_manager.build_short_term_memory(
                current_number=chapter_num,
                stm_chapter_count=self.setup.short_term_memory_chapters,
                max_chars=self.setup.short_term_memory_max_chars
            )

            if stm:
                print(f"📝 Short-term memory activation: recent {self.setup.short_term_memory_chapters} chapters ({len(stm)} chars)")
            else:
                print(f"📝 Short-term memory: no previous chapters")
            return stm
        except Exception as e:
            print(f"⚠️ Errors in short-term memory creation: {e}")
            return ""

    def _prepare_long_term_memory(self) -> str:
        """Long-term memory preparation"""
        try:
            ltm = extract_long_term_memory(self.memory_manager)
            ltm_formatted = format_long_term_memory_for_prompt(ltm)

            if ltm_formatted:
                print(f"🧠 Activating long-term memory: including character development and plot progression")
            else:
                print(f"🧠 Long-term memory: no information has been accumulated yet")
            return ltm_formatted
        except Exception as e:
            print(f"⚠️ Error extracting long-term memory: {e}")
            return ""

    def _calculate_target_words(self):
        """Calculate target characters size"""
        min_words = int(self.setup.target_words_per_chapter * (1 - self.setup.words_tolerance))
        max_words = int(self.setup.target_words_per_chapter * (1 + self.setup.words_tolerance))
        return (min_words, max_words)

    def _write_and_refine_chapter(self, chapter, context, target_words,
                                  short_term_memory, long_term_memory, next_outline):
        """Chapter Writing and Editing"""
        # Drafting
        current_content = self.writer.write_chapter(
            chapter=chapter,
            context=context,
            target_words=target_words,
            short_term_memory=short_term_memory,
            long_term_memory=long_term_memory,
            next_chapter_outline=next_outline
        )
        chapter.content = current_content

        # Review-Revision Cycle
        refinement_round = 0
        min_words, max_words = target_words

        while refinement_round < self.config.max_refinement_rounds:
            try:
                review = self.editor.review_content(
                    chapter, context, target_words,
                    short_term_memory=short_term_memory,
                    long_term_memory=long_term_memory
                )

                if not review or not isinstance(review, dict):
                    print("⚠️ The review results are incorrect. Proceeding with the default values.")
                    review = {
                        'average_score': 7.0,
                        'status': 'Needs revision',
                        'feedback_text': 'Review failed',
                        'scores': [7.0]
                    }

                # Check the quantity and score
                word_count = count_words(chapter.content)
                chapter.word_count = word_count

                length_ok = min_words <= word_count <= max_words
                score_ok = review.get('average_score', 0) >= self.config.approval_score_threshold

                if review.get('status') == 'Approved' and score_ok and length_ok:
                    print(f"\n✅ Approved (Score: {review.get('average_score', 0):.1f}/10, Quantity: {word_count}words)")
                    break

                print(f"\n🔄 Revision round {refinement_round + 1}/{self.config.max_refinement_rounds}")
                feedback_preview = str(review.get('feedback_text', ''))[:150]
                print(f"Feedback: {feedback_preview}...")

                current_content = self.writer.refine_chapter(chapter, review, target_words)
                chapter.content = current_content
                chapter.word_count = count_words(current_content)
                refinement_round += 1

            except Exception as e:
                print(f"⚠️ An error occurred during review/editing: {e}")
                print("   Proceed with the current content.")
                break

    def _summarize_and_update_memory(self, chapter):
        """Chapter Summary and Memory Update"""
        print(f"📊 Generating chapter summary...")
        try:
            summary_data = self.summarizer.summarize_chapter(chapter)
            chapter.summary = summary_data.get('summary', '')
            chapter.key_events = summary_data.get('key_events', [])

            try:
                self.memory_manager.update_from_summary(summary_data)
                print(f"✓ Memory update complete")
            except AttributeError as e:
                print(f"⚠️ Error updating memory: {e}")
                print(f"   Save summary information only and proceed.")
        except Exception as e:
            print(f"⚠️ Error generating summary: {e}")
            chapter.summary = f"Chapter {chapter.number} Summary generation failed"
            chapter.key_events = []

    def _optimize_memory(self, chapter_num: int):
        """Long-term memory optimization"""
        print(f"\n{'=' * 60}")
        print(f"🧠 Perform long-term memory optimization (when chapter {chapter_num} is completed)")
        print(f"{'=' * 60}")

        try:
            optimization_result = self.ltm_optimizer.optimize_memory(
                self.memory_manager,
                self.chapter_manager,
                chapter_num
            )

            if optimization_result.get('success'):
                self.state_manager.save_state(self.chapter_manager, self.memory_manager)
                print("✓ Optimization and saving complete")
        except Exception as e:
            print(f"⚠️ Error during memory optimization: {e}")
            print("  Keep the original memory and proceed.")

    def _save_final_novel(self):
        """Save the final novel"""
        print("\n" + "=" * 60)
        print("🎉 Completed writing the novel!")
        print("=" * 60)

        self.chapter_manager.print_length_report()

        print(f"\n🚀 Save the final novel as '{self.output_file}'...")
        final_content = []
        for ch in self.chapter_manager.get_completed_chapters():
            final_content.append(f"# Chapter {ch.number}: {ch.title}\n")
            final_content.append(ch.content.strip())
            final_content.append("\n\n" + "=" * 80 + "\n")

        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write("\n".join(final_content))

        print(f"✓ Saving complete. Check {self.output_file}.")
        print("\n" + "=" * 60)

    def _handle_interruption(self):
        """Handling user interruptions"""
        print("\n\n⚠️ Stopped by the user.")
        print("💾 Save the work so far...")
        self.state_manager.save_state(self.chapter_manager, self.memory_manager)
        print("✓ Save complete. You can continue writing later.")

    def _handle_error(self, e: Exception):
        """Handling error"""
        print(f"\n❌ A fatal error occurred: {e}")
        import traceback
        traceback.print_exc()

        print("\n💾 Operation stopped. Saving final state...")
        self.state_manager.save_state(self.chapter_manager, self.memory_manager)
        print("✓ Save complete. Please try again after resolving any issues.")