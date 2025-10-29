# coding=utf-8
"""
Long-term memory management utility
"""

from novel_writer.memory_manager import NovelMemoryManager


def extract_long_term_memory(mm: NovelMemoryManager) -> dict:
    """
    Extracting long-term memory (character_development, plot_threads) from NovelMemoryManager
    """
    try:
        memory_dict = mm.to_dict()

        # If a list is returned (incorrect implementation)
        if isinstance(memory_dict, list):
            print("  ⚠️ memory_dict is a list. Switch to direct attribute access.")
            long_term_memory = {
                'character_development': getattr(mm, 'character_development', {}),
                'plot_threads': getattr(mm, 'plot_threads', {})
            }
        # If a dict is returned (normal)
        elif isinstance(memory_dict, dict):
            long_term_memory = {
                'character_development': memory_dict.get('character_development', {}),
                'plot_threads': memory_dict.get('plot_threads', {})
            }
        else:
            print(f"  ⚠️ unexpected type: {type(memory_dict)}")
            long_term_memory = {
                'character_development': {},
                'plot_threads': {}
            }

        return long_term_memory

    except Exception as e:
        print(f"  ⚠️ Error extracting long-term memory: {e}")
        return {
            'character_development': {},
            'plot_threads': {}
        }


def format_long_term_memory_for_prompt(ltm: dict) -> str:
    """
    Convert long-term memory to a string format to be inserted into the prompt    """
    if not ltm or not isinstance(ltm, dict):
        return ""

    sections = []

    try:
        # Character development status
        char_dev = ltm.get('character_development', {})
        if char_dev and isinstance(char_dev, dict):
            sections.append("--- Character Development Status (Long-Term Memory) ---")
            for char_name, developments in char_dev.items():
                if developments:
                    if isinstance(developments, list):
                        try:
                            recent_devs = developments[-3:] if len(developments) > 3 else developments
                            if recent_devs:
                                sections.append(f"• {char_name}: {', '.join(str(d) for d in recent_devs)}")
                        except Exception as e:
                            print(f"  ⚠️ Character development format error ({char_name}): {e}")
                            sections.append(f"• {char_name}: {str(developments)}")
                    elif isinstance(developments, str):
                        sections.append(f"• {char_name}: {developments}")
                    else:
                        sections.append(f"• {char_name}: {str(developments)}")

        # 진행 중인 플롯
        plot_threads = ltm.get('plot_threads', {})
        if plot_threads:
            sections.append("\n--- Ongoing plot (long-term memory) ---")

            try:
                # If plot_threads is a dict
                if isinstance(plot_threads, dict):
                    for thread_name, status in plot_threads.items():
                        if thread_name and status:
                            sections.append(f"• {thread_name}: {status}")

                # If plot_threads is a list
                elif isinstance(plot_threads, list):
                    for item in plot_threads:
                        if isinstance(item, dict):
                            thread_name = item.get('thread', item.get('name', ''))
                            status = item.get('status', '')
                            if thread_name:
                                sections.append(f"• {thread_name}: {status}")
                        elif isinstance(item, str) and item:
                            sections.append(f"• {item}")
            except Exception as e:
                print(f"  ⚠️Plot thread format error: {e}")
                sections.append(f"• Plot information: {str(plot_threads)[:100]}...")

    except Exception as e:
        print(f"  ⚠️ Error formatting long-term memory: {e}")
        import traceback
        traceback.print_exc()
        return ""

    return "\n".join(sections) if sections else ""