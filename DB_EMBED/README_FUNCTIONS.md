# Thuvien Phap Luat Crawler - All Functions

This crawler has multiple functions for scraping different types of legal data from thuvienphapluat.vn

## 📋 Available Scripts

### 1. **Scrape Q&A (Legal Questions & Answers)**
```bash
python test_get_qa_no_proxy.py
```
**What it does:**
- Scrapes Q&A from multiple legal domains
- Saves questions, answers, dates, and URLs
- Output: `./tvpl_qa_ver3_testing/`

**Already scraped:** ~5,167 questions across 5 domains ✅

---

### 2. **Scrape Latest Laws** 
```bash
python test_get_latest_laws.py
```
**What it does:**
- Gets all laws effective from June 1, 2025 onwards
- Saves law URLs to JSONL file
- Output: `./latest_laws/`

**Status:** Ready to run

---

### 3. **Scrape Not-Yet-Effective Laws**
```bash
python test_get_not_effective_laws.py
```
**What it does:**
- Gets all laws that will take effect in the future
- Saves law URLs to JSONL file
- Output: `./not_yet_effective_laws/`

**Status:** Ready to run

---

### 4. **Scrape All Legal Documents (Advanced)**
```python
# In main.py
crawler.craw_all_data(
    search_type=1,      # 1=all laws, 2=draft laws, 3=official dispatches, 4=standards
    max_workers=5,
    keyword="",
    category={"fields": "0", "total": "1000"},
    install_all=False
)
```
**What it does:**
- Scrapes complete legal documents with:
  - Full text (HTML)
  - PDF files
  - Law diagrams
  - Effectiveness status
  - Related documents
- Very comprehensive but slower

**Status:** Available for advanced use

---

## 🎯 What You've Accomplished

✅ **Successfully scraped 5,167+ Q&A questions** across:
- Banking & Currency (855 questions)
- Civil Rights (1,662 questions)
- Securities (380 questions)
- Intellectual Property (1,132 questions)
- State Finance (1,138 questions)

## 🚀 Next Steps

You can now:

1. **Continue with Q&A scraping** - Add more domains to `qa_domain/domains_qa.json`

2. **Scrape latest laws** - Run `test_get_latest_laws.py`

3. **Scrape future laws** - Run `test_get_not_effective_laws.py`

4. **Deep dive into specific laws** - Use the advanced `craw_all_data()` function

## 📁 Output Folders

```
Simple Crawl TVPL/
├── tvpl_qa_ver3_testing/          # Q&A data
├── latest_laws/                    # Latest effective laws
├── not_yet_effective_laws/         # Future laws
└── data/                           # Advanced legal documents
    ├── data_tvpl/                  # All laws
    ├── data_duthao/                # Draft laws
    ├── data_congvan/               # Official dispatches
    └── data_tieuchuan/             # Standards
```

## ⚙️ Configuration

### Credentials
- Username: `dawng123`
- Password: `123456`

### Proxy Settings
- Currently running **WITHOUT proxy** (works fine!)
- Can enable proxy in code if needed

### Max Workers
- Default: 3 workers (parallel processing)
- Can increase for faster scraping

## 🐛 Known Issues

1. **Encoding errors** - Some Vietnamese characters with special marks may fail (very rare)
2. **500 errors** - Occasional server errors from the website (retries enabled)
3. **Timeouts** - Normal when scraping without proxy (retries enabled)

All issues have automatic retry mechanisms!

## 📊 Data Formats

All data is saved in both:
- **JSONL** (efficient, one JSON per line)
- **JSON** (compatible, full array)

## 🎓 Usage Examples

See the test files for working examples:
- `test_get_qa_no_proxy.py` - Q&A scraping
- `test_get_latest_laws.py` - Latest laws
- `test_get_not_effective_laws.py` - Future laws
- `test_with_proxy.py` - Using authenticated proxy

---

**Happy Scraping! 🚀**
