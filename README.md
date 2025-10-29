# 🤖 AI Novel Automatic Writing System v0.1.0

This is an AI-powered automatic novel writing system. It offers features such as long-term and short-term memory management, automatic structure generation, and iterative quality improvement.

## ✨ Key Features

### 📚 Intelligent Memory Management
- **Short-Term Memory**: Tracks recent chapter content to prevent duplication.
- **Long-Term Memory**: Manages character development and plot threads.
- **Automatic Optimization**: Compacts and organizes memory at set intervals.

### ✍️ Automatic Writing Process
- **Structure Generation**: Automatically generates chapter structures based on synopsis.
- **Write-Review-Revise**: AI-generated content is reviewed and improved.
- **Maintain Consistency**: Write while maintaining the overall plot and character settings.

### 💾 Pause/Resume Functionality
- **Auto-Save**: Saves progress at set intervals.
- **Continue Writing**: Resume work where you left off.
- **Safe Stop**: Automatically saves when interrupted with Ctrl+C.

### 🎯 Quality Control
- **Quantity Control**: Set target word count and tolerance.
- **Score-Based Approval**: Approves only those with a set score or higher.
- **Multiple Revision Rounds**: Set a maximum number of revisions. Available

## 📋 Requirements

### Python Packages
```bash
pip install google-generativeai
```

### API Key
You need a Gemini API key:
```bash
export GEMINI_API_KEY="your_api_key_here"
```

## 🚀 Getting Started

### 1. Installation
```bash
git clone https://github.com/yourusername/novel-writer.git
cd novel-writer
pip install -r requirements.txt
```

### 2. Setting up environment variables
```bash
export GEMINI_API_KEY="your_gemini_api_key"
```

### 3. Novel Setup
Edit the novel's default settings in `config.py`:

```python
setup = NovelSetup(
synopsis="Your novel synopsis...",
writing_style="Describe your writing style...",
characters=[...],
world_setting="Describe your world...",
target_chapters=15,
target_words_per_chapter=1000,
...
)
```

### 4. Execution
```bash
python main.py
```

## 📁 Project Structure

```
novel-writer/
├── main.py # Main executable
├── config.py # Novel settings
├── pipeline.py # Writing pipeline
├── state_utils.py # Save/load state
├── memory_utils.py # Memory management
├── novel_writer/ # Core libraries
│ ├── client_setup.py # API client
│ ├── writer.py # Writer module
│ ├── writer_config.py # Configuration module
│ ├── editor.py # Editor module
│ ├── summarizer.py # Summary module
│ ├── structure_generator.py # Structure generation
│ ├── chapter_manager.py # Chapter management
│ ├── memory_manager.py # Memory management
│ └── utils.py # Utility functions
├── novel_state.json # Saved progress
└── final_novel.txt # Completed novel
```

## ⚙️ Main Settings

### NovelSetup
| Parameters | Description | Default |
|---------|------|--------|
| `synopsis` | Full synopsis of the novel | - |
| `writing_style` | Writing style guidelines | - |
| `characters` | Character list | - |
| `world_setting` | World setting description | - |
| `target_chapters` | Target number of chapters | 15 |
| `target_words_per_chapter` | Target word count per chapter | 1000 |
| `words_tolerance` | Length tolerance (ratio) | 0.2 |
| `short_term_memory_chapters` | Short-term memory range | 3 |
| `enable_ltm_optimization` | Enable long-term memory optimization | True |

### WriterConfig
| Parameters | Description | Default |
|---------|------|--------|
| `writer_model` | AI model for authoring | gemini-2.5-flash-lite |
| `editor_model` | AI model for reviewing | gemini-2.5-flash-lite |
| `max_generation_tokens` | Maximum token generation | 8000 |
| `rate_limit_delay` | Wait time between API calls (in seconds) | 10.0 |
| `auto_save_interval` | Autosave Interval (Chapter Number) | 1 |
| `max_refinement_rounds` | Maximum Number of Revisions | 2 |
| `approval_score_threshold` | Approval Score Threshold | 7.0 |
| `ltm_optimization_interval` | Memory Optimization Interval | 5 |

## 💡 Usage Examples

### Basic Usage
```python
from config import setup_novel
from pipeline import NovelPipeline

# Loading Settings
setup, config = setup_novel()

# Running the Pipeline
pipeline = NovelPipeline(
setup=setup,
config=config,
state_file="my_novel_state.json",
output_file="my_novel.txt"
)

pipeline.run()
```

### Running with Custom Settings
```python
# After modifying config.py
setup = NovelSetup(
synopsis="Sci-Fi Thriller: A Future Where AI Dominates Humans...",
target_chapters=20,
target_words_per_chapter=1500,
writing_style="Suspenseful and Fast-paced"
)
```

## 🔧 Advanced Features

### Memory Optimization
Long-term memory is automatically optimized at set intervals:
- Only important character development is retained
- Completed plot threads are cleaned up
- Memory size is maintained

### Interruption and Resume
When interrupting a task:
1. Safely interrupt with `Ctrl+C`
2. Progress is automatically saved
3. Resume writing when `python main.py` is run again

### State File Management
```python
# Start from scratch
rm novel_state.json
python main.py

# Start from a specific state
cp backup_state.json novel_state.json
python main.py
```

## 📊 Output Format

The completed novel is saved in the following format:

```
# Chapter 1: Start
Chapter Contents...

==============================================================================================

# Chapter 2: Development
Chapter Contents...

= ... max_retries=10,
retry_delay=30.0
)
```

### Memory Error
```python
# Reduce Short-Term Memory Size
setup = NovelSetup(
short_term_memory_max_chars=2000,
short_term_memory_chapters=2
)
```

### Quality Improvements
```python
# Apply Stricter Standards
config = WriterConfig(
max_refinement_rounds=3,
approval_score_threshold=8.0
)
```

## 🤝 Contribute

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is distributed under the MIT License. See the `LICENSE` file for details.

## 🙏 Acknowledgements

- Google Gemini API
- All contributors

## 📧 Contact Us

For project inquiries: [fragrantmaro@naver.com](fragrantmaro@naver.com)

Project Link: [https://github.com/marohan/llm_novel_writer](https://github.com/marhan/llm_novel_writer)

LinkedIn: [https://www.linkedin.com/in/marohan-min-a5b04533a/](https://www.linkedin.com/in/marohan-min-a5b04533a/)
