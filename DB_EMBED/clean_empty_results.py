"""
Clean Empty Results from Scraper Output Files
Removes all entries with no content or only paywall text from:
1. Content extractor results (traffic_laws_WITH_CONTENT_*)
2. Original scraper results (traffic_laws_*)
Also removes URLs with empty content from processed_content_urls.txt
"""

import json
import os
import glob
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(f"cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler(),
    ],
)


class ResultsCleaner:
    def __init__(self):
        self.paywall_markers = [
            "Các nội dung của văn bản này được văn bản khác thay đổi",
            "Được hỗ trợ pháp lý sơ bộ qua Điện thoại",
            "Nhận thông báo văn bản mới qua Email",
            "Trang cá nhân",
            "gói dịch vụ",
        ]

        self.dialog_phrase = (
            "Beginning of dialog window. Escape will cancel and close the window.\n\n"
        )

        self.stats = {
            "total_files_processed": 0,
            "total_entries_before": 0,
            "total_entries_after": 0,
            "removed_empty": 0,
            "removed_paywall": 0,
            "removed_short": 0,
        }

        self.removed_urls = set()  # Track URLs to remove from processed list

    def _is_paywall_content(self, content):
        """Check if content is paywall text"""
        if not content:
            return False

        if len(content) < 2000:
            markers_found = sum(
                1 for marker in self.paywall_markers if marker in content
            )
            if markers_found >= 2:
                return True
        return False

    def _clean_content(self, content):
        """Remove dialog window phrase from content"""
        if content and self.dialog_phrase in content:
            content = content.replace(self.dialog_phrase, "")
        return content

    def _is_valid_entry(self, entry):
        """Check if entry has valid content"""
        content = entry.get("content", "")
        content_length = entry.get("content_length", 0)

        # Check for empty content
        if not content or content_length == 0:
            self.stats["removed_empty"] += 1
            # Track URL for removal from processed list
            url = entry.get("url", "")
            if url:
                self.removed_urls.add(url)
            return False

        # Check for paywall content
        if self._is_paywall_content(content):
            self.stats["removed_paywall"] += 1
            return False

        # Check for very short content (likely incomplete)
        if content_length < 500:
            self.stats["removed_short"] += 1
            return False

        return True

    def clean_json_file(self, filepath):
        """Clean a single JSON file"""
        try:
            logging.info(f"[PROCESSING] {filepath}")

            # Load data
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                logging.warning(f"[SKIP] Not a list: {filepath}")
                return

            before_count = len(data)
            self.stats["total_entries_before"] += before_count

            # Filter valid entries and clean content
            cleaned_data = []
            for entry in data:
                if self._is_valid_entry(entry):
                    # Clean the content by removing dialog phrase
                    entry["content"] = self._clean_content(entry.get("content", ""))
                    cleaned_data.append(entry)

            after_count = len(cleaned_data)
            self.stats["total_entries_after"] += after_count
            removed_count = before_count - after_count

            # Create backup (remove old backup if exists)
            backup_path = filepath + ".backup"
            if os.path.exists(backup_path):
                os.remove(backup_path)
                logging.info(f"[BACKUP] Removed old backup: {backup_path}")
            os.rename(filepath, backup_path)
            logging.info(f"[BACKUP] Created: {backup_path}")

            # Save cleaned data
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

            logging.info(
                f"[OK] Cleaned: {before_count} -> {after_count} (removed {removed_count})"
            )
            self.stats["total_files_processed"] += 1

        except Exception as e:
            logging.error(f"[ERROR] Failed to clean {filepath}: {e}")

    def clean_jsonl_file(self, filepath):
        """Clean a single JSONL file"""
        try:
            logging.info(f"[PROCESSING] {filepath}")

            # Load data
            data = []
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue

            before_count = len(data)
            self.stats["total_entries_before"] += before_count

            # Filter valid entries and clean content
            cleaned_data = []
            for entry in data:
                if self._is_valid_entry(entry):
                    # Clean the content by removing dialog phrase
                    entry["content"] = self._clean_content(entry.get("content", ""))
                    cleaned_data.append(entry)

            after_count = len(cleaned_data)
            self.stats["total_entries_after"] += after_count
            removed_count = before_count - after_count

            # Create backup (remove old backup if exists)
            backup_path = filepath + ".backup"
            if os.path.exists(backup_path):
                os.remove(backup_path)
                logging.info(f"[BACKUP] Removed old backup: {backup_path}")
            os.rename(filepath, backup_path)
            logging.info(f"[BACKUP] Created: {backup_path}")

            # Save cleaned data
            with open(filepath, "w", encoding="utf-8") as f:
                for entry in cleaned_data:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")

            logging.info(
                f"[OK] Cleaned: {before_count} -> {after_count} (removed {removed_count})"
            )
            self.stats["total_files_processed"] += 1

        except Exception as e:
            logging.error(f"[ERROR] Failed to clean {filepath}: {e}")

    def find_and_clean_all(self):
        """Find and clean all scraper output files"""
        logging.info("[START] Searching for scraper output files...")

        # Find all output directories
        content_dirs = glob.glob("traffic_laws_WITH_CONTENT_*")
        scraper_dirs = glob.glob("traffic_laws_2*")

        all_dirs = content_dirs + scraper_dirs

        if not all_dirs:
            logging.warning("[WARNING] No output directories found!")
            return

        logging.info(f"[FOUND] {len(all_dirs)} output directories")

        # Process each directory
        for dir_path in all_dirs:
            logging.info(f"\n[DIR] Processing: {dir_path}")

            # Clean JSON files
            json_files = glob.glob(os.path.join(dir_path, "*.json"))
            for json_file in json_files:
                if not json_file.endswith(".backup"):
                    self.clean_json_file(json_file)

            # Clean JSONL files
            jsonl_files = glob.glob(os.path.join(dir_path, "*.jsonl"))
            for jsonl_file in jsonl_files:
                if not jsonl_file.endswith(".backup"):
                    self.clean_jsonl_file(jsonl_file)

        # Print summary
        self.print_summary()

        # Clean processed URLs file
        self.clean_processed_urls()

    def clean_processed_urls(self):
        """Remove URLs with empty content from processed_content_urls.txt"""
        processed_file = "processed_content_urls.txt"

        if not os.path.exists(processed_file):
            logging.info(f"[SKIP] {processed_file} not found")
            return

        if not self.removed_urls:
            logging.info(f"[SKIP] No URLs to remove from {processed_file}")
            return

        try:
            # Read all processed URLs
            with open(processed_file, "r", encoding="utf-8") as f:
                all_urls = set(line.strip() for line in f if line.strip())

            before_count = len(all_urls)

            # Remove the empty content URLs
            cleaned_urls = all_urls - self.removed_urls

            after_count = len(cleaned_urls)
            removed_count = before_count - after_count

            if removed_count > 0:
                # Create backup
                backup_file = processed_file + ".backup"
                if os.path.exists(backup_file):
                    os.remove(backup_file)
                os.rename(processed_file, backup_file)

                # Write cleaned URLs
                with open(processed_file, "w", encoding="utf-8") as f:
                    for url in sorted(cleaned_urls):
                        f.write(url + "\n")

                logging.info(
                    f"[CLEANED] {processed_file}: {before_count} -> {after_count} (removed {removed_count} URLs)"
                )
            else:
                logging.info(f"[OK] {processed_file}: No changes needed")

        except Exception as e:
            logging.error(f"[ERROR] Failed to clean {processed_file}: {e}")

    def print_summary(self):
        """Print cleanup summary"""
        logging.info("\n" + "=" * 60)
        logging.info("[CLEANUP SUMMARY]")
        logging.info("=" * 60)
        logging.info(f"Files processed: {self.stats['total_files_processed']}")
        logging.info(f"Total entries before: {self.stats['total_entries_before']}")
        logging.info(f"Total entries after: {self.stats['total_entries_after']}")
        logging.info(
            f"Total removed: {self.stats['total_entries_before'] - self.stats['total_entries_after']}"
        )
        logging.info(f"  - Empty content: {self.stats['removed_empty']}")
        logging.info(f"  - Paywall content: {self.stats['removed_paywall']}")
        logging.info(f"  - Short content (<500 chars): {self.stats['removed_short']}")
        logging.info("=" * 60)
        logging.info("\n[NOTE] Original files backed up with .backup extension")


def main():
    logging.info("[CLEANUP] Starting cleanup process...")

    cleaner = ResultsCleaner()
    cleaner.find_and_clean_all()

    logging.info("\n[DONE] Cleanup complete!")
    logging.info(
        "[TIP] To restore backups, rename .backup files back to original names"
    )


if __name__ == "__main__":
    main()
