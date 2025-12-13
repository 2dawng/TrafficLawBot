# Crawl Data Location Configuration

## ✅ **All crawl data has been moved to: `D:\crawl`**

### **Current Folder Structure:**

```
D:\crawl\
├── tvpl_qa_ver3_testing\         # Q&A Data (5,167+ questions)
│   ├── Tiền tệ - Ngân hàng\      # Banking & Currency (855)
│   ├── Quyền dân sự\              # Civil Rights (1,662)
│   ├── Chứng khoán\               # Securities (380)
│   ├── Sở hữu trí tuệ\            # Intellectual Property (1,132)
│   └── Tài chính nhà nước\        # State Finance (1,138)
│
├── latest_laws\                   # Latest laws (in progress)
│   └── all_law_from_0_to_50.jsonl
│
└── not_yet_effective_laws\        # Future laws (when you run it)
```

---

## 📝 **Updated Scripts:**

All scripts now save to `D:\crawl`:

### **1. Q&A Scraping**
```bash
python test_get_qa_no_proxy.py
```
- Saves to: `D:\crawl\tvpl_qa_ver3_testing\`

### **2. Latest Laws**
```bash
python test_get_latest_laws.py
```
- Saves to: `D:\crawl\latest_laws\`

### **3. Not-Yet-Effective Laws**
```bash
python test_get_not_effective_laws.py
```
- Saves to: `D:\crawl\not_yet_effective_laws\`

### **4. With Proxy (if needed)**
```bash
python test_with_proxy.py
```
- Saves to: `D:\crawl\tvpl_qa_ver3_testing\`

---

## ✅ **Benefits:**

1. ✅ All data in one centralized location (`D:\crawl`)
2. ✅ Easy to backup/manage
3. ✅ Scripts will automatically resume from existing data
4. ✅ No need to worry about C: drive space

---

## 🔄 **Resume Feature:**

All scripts automatically resume from where they left off:
- Existing URLs/questions are detected
- Only new data is scraped
- Progress is saved incrementally

---

## 📊 **Check Your Data:**

To see what you have:
```powershell
# List all folders
ls D:\crawl

# Count Q&A questions
ls D:\crawl\tvpl_qa_ver3_testing\*\*.json

# Count law URLs
(Get-Content "D:\crawl\latest_laws\all_law_from_0_to_50.jsonl").Count
```

---

**All set! Your crawl data is now in `D:\crawl` and all scripts are configured to use it.** 🚀
