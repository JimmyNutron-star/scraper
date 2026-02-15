# odibets_github_scraper.py
"""
Odibets Integrated Scraper - GitHub Actions Optimized Version
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
from datetime import datetime
import json
import logging
from pathlib import Path
import os
import sys
import traceback


class OdibetsGithubScraper:
    """
    Odibets Scraper optimized for GitHub Actions
    """
    
    def __init__(self, mode='full'):
        self.mode = mode
        self.url = "https://odibets.com/odileague"
        self.driver = None
        self.wait = None
        
        # Timer tracking
        self.current_pre_timer = None
        self.current_live_timer = None
        self.prematch_active = False
        self.live_mode_active = False
        self.selected_timestamp = None
        self.selected_timestamp_index = 2
        self.timer_reached_zero = False
        self.kickoff_time = None
        
        # Match tracking
        self.goal_count = 0
        self.previous_scores = {}
        
        # Results directory
        self.results_dir = Path("odibets_scraped_data")
        self.results_dir.mkdir(exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        
        # Execution timeout (GitHub Actions limit is 6 hours, but we'll set a reasonable limit)
        self.start_time = time.time()
        self.max_execution_time = 3300  # 55 minutes (under 1 hour)
    
    def setup_logging(self):
        """Setup logging configuration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.results_dir / f"github_scraper_{timestamp}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("OdibetsGithub")
    
    def check_timeout(self):
        """Check if we're approaching the GitHub Actions time limit"""
        elapsed = time.time() - self.start_time
        if elapsed > self.max_execution_time:
            self.logger.warning(f"Approaching time limit ({elapsed:.0f}s), saving data and exiting")
            return True
        return False
    
    def setup_driver(self):
        """Configure Chrome WebDriver for GitHub Actions"""
        chrome_options = Options()
        
        # Required for GitHub Actions
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--disable-software-rasterizer")
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            # Use webdriver-manager to automatically handle ChromeDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 20)
            self.logger.info("Chrome driver initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome driver: {e}")
            print("\n❌ ERROR: Chrome driver initialization failed.")
            print(f"   Error: {e}")
            raise
    
    def handle_popup(self):
        """Close popup if present"""
        try:
            time.sleep(2)
            close_button = self.driver.find_element(By.CSS_SELECTOR, ".roadblock-close button")
            close_button.click()
            self.logger.info("Popup closed successfully")
            time.sleep(1)
            return True
        except:
            self.logger.debug("No popup found")
            return False
    
    # [Include all the other methods from the original scraper here]
    # For brevity, I'll include the key methods but you should copy all methods
    # from your original integrated scraper into this class
    
    def format_goal_selection(self, market_name, label):
        """Format selection text specifically for goal markets"""
        market_lower = market_name.lower()
        label_lower = label.lower()
        
        # OV/UN markets
        if 'ov/un' in market_lower or 'over/under' in market_lower:
            if 'over' in label_lower or 'ov' in label_lower or label == 'O':
                return f"Over {market_name.replace('OV/UN ', '').replace('Over/Under ', '')} Goals"
            elif 'under' in label_lower or 'un' in label_lower or label == 'U':
                return f"Under {market_name.replace('OV/UN ', '').replace('Over/Under ', '')} Goals"
        
        # GG/NG
        elif 'gg/ng' in market_lower:
            if label == 'Yes':
                return "Both Teams to Score - Yes"
            elif label == 'No':
                return "Both Teams to Score - No"
        
        # First Team to Score
        elif 'first team to score' in market_lower:
            if 'home' in label_lower or label == '1' or 'home' in label:
                return "First Team to Score - Home"
            elif 'away' in label_lower or label == '2' or 'away' in label:
                return "First Team to Score - Away"
            elif 'no goal' in label_lower or label == 'NG' or 'no' in label_lower:
                return "First Team to Score - No Goal"
        
        # Total Goals (exact)
        elif 'total goals' in market_lower and 'odd/even' not in market_lower:
            if '+' in label:
                return f"Exact Total Goals - {label}"
            else:
                return f"Exact Total Goals - {label} Goal{'s' if label != '1' else ''}"
        
        # Total Goals Odd/Even
        elif 'odd/even' in market_lower:
            return f"Total Goals - {label}"
        
        # Multi-Goals
        elif 'multi-goals' in market_lower:
            return f"Multi-Goals - {label}"
        
        # Time of First Goal
        elif 'time of first goal' in market_lower:
            return f"First Goal in {label}"
        
        # Team-specific OV/UN
        elif 'team 1' in market_lower:
            if 'over' in label_lower or 'ov' in label_lower or label == 'O':
                return "Home Team Over 1.5 Goals"
            elif 'under' in label_lower or 'un' in label_lower or label == 'U':
                return "Home Team Under 1.5 Goals"
        elif 'team 2' in market_lower:
            if 'over' in label_lower or 'ov' in label_lower or label == 'O':
                return "Away Team Over 1.5 Goals"
            elif 'under' in label_lower or 'un' in label_lower or label == 'U':
                return "Away Team Under 1.5 Goals"
        
        # Combination markets
        elif '1x2 and' in market_lower or '1x2 &' in market_lower:
            if '1' in label:
                return f"Home Win + {market_name.split('OV/UN')[1].strip() if 'OV/UN' in market_name else ''} Goals"
            elif 'x' in label_lower:
                return f"Draw + {market_name.split('OV/UN')[1].strip() if 'OV/UN' in market_name else ''} Goals"
            elif '2' in label:
                return f"Away Win + {market_name.split('OV/UN')[1].strip() if 'OV/UN' in market_name else ''} Goals"
        
        # 1X2 & No Goal
        elif '1x2 & no goal' in market_lower:
            if '1' in label:
                return "Home Win & No Goal"
            elif 'x' in label_lower:
                return "Draw & No Goal"
            elif '2' in label:
                return "Away Win & No Goal"
        
        return f"{market_name} - {label}"
    
    # NOTE: You need to copy ALL the other methods from your original 
    # OdibetsIntegratedScraper class here:
    # - extract_goal_odds_fallback
    # - scrape_goal_markets
    # - get_prematch_timer
    # - get_live_minutes
    # - monitor_timer
    # - get_live_matches
    # - check_goals
    # - track_live_matches
    # - navigate_to_tab
    # - scrape_standings
    # - scrape_results
    # - save_standings_report
    # - scrape_results_and_standings
    
    def run(self):
        """Main execution flow for GitHub Actions"""
        overall_start = time.time()
        
        self.logger.info("="*80)
        self.logger.info(f"🏆 ODIBETS GITHUB SCRAPER - Mode: {self.mode}")
        self.logger.info("="*80)
        
        try:
            # Setup driver
            self.setup_driver()
            
            # Load page
            self.logger.info(f"Loading {self.url}")
            self.driver.get(self.url)
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".virtual-timer"))
            )
            self.handle_popup()
            
            results = {}
            
            # Execute based on mode
            if self.mode in ['full', 'goals_only']:
                self.logger.info("PHASE 1: Goal Markets Scraping")
                match_details, goal_markets_data, timestamp_text = self.scrape_goal_markets()
                results['goal_markets'] = {
                    'success': match_details is not None,
                    'timestamp': timestamp_text
                }
                
                if self.check_timeout():
                    self.save_summary(results)
                    return
            
            if self.mode in ['full', 'live_only'] and self.mode != 'goals_only':
                if self.mode == 'full' and match_details:
                    self.logger.info("PHASE 2: Timer Monitoring")
                    self.monitor_timer(match_details)
                    
                    if self.check_timeout():
                        self.save_summary(results)
                        return
                    
                    self.logger.info("PHASE 3: Live Match Tracking")
                    self.track_live_matches()
                    results['live_tracking'] = {
                        'goals_detected': self.goal_count,
                        'kickoff_time': self.kickoff_time
                    }
            
            if self.mode in ['full', 'results_only']:
                self.logger.info("PHASE 4: Results & Standings Scraping")
                time.sleep(5)  # Wait for updates
                results_data, standings_data = self.scrape_results_and_standings()
                results['results_standings'] = {
                    'results_success': results_data is not None,
                    'standings_success': standings_data is not None
                }
            
            # Save execution summary
            self.save_summary(results)
            
            total_time = time.time() - overall_start
            self.logger.info("="*80)
            self.logger.info(f"✅ SCRAPING COMPLETED in {total_time:.2f} seconds")
            self.logger.info("="*80)
            
        except Exception as e:
            self.logger.error(f"Error in main execution: {e}")
            traceback.print_exc()
            self.save_error_log(str(e))
        finally:
            if self.driver:
                self.driver.quit()
                self.logger.info("Browser closed")
    
    def save_summary(self, results):
        """Save execution summary"""
        summary_file = self.results_dir / f"execution_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        summary = {
            'execution_time': datetime.now().isoformat(),
            'mode': self.mode,
            'results': results,
            'timestamp_selected': self.selected_timestamp,
            'goals_detected': self.goal_count
        }
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        self.logger.info(f"Summary saved to {summary_file}")
    
    def save_error_log(self, error_message):
        """Save error information"""
        error_file = self.results_dir / f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        with open(error_file, 'w') as f:
            f.write(f"Error Time: {datetime.now().isoformat()}\n")
            f.write(f"Mode: {self.mode}\n")
            f.write(f"Error: {error_message}\n")
            f.write(f"Traceback: {traceback.format_exc()}\n")
        self.logger.info(f"Error log saved to {error_file}")


def main():
    """Main entry point for GitHub Actions"""
    # Get mode from environment variable
    mode = os.environ.get('SCRAPING_MODE', 'full')
    
    print(f"\n{'='*80}")
    print(f"ODIBETS GITHUB SCRAPER - Mode: {mode}")
    print('='*80)
    
    scraper = OdibetsGithubScraper(mode=mode)
    
    try:
        scraper.run()
    except KeyboardInterrupt:
        print("\n\n⏹️ Scraper stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        traceback.print_exc()
    finally:
        print("\n" + "="*80)
        print("✅ Script finished")
        print("="*80 + "\n")


if __name__ == "__main__":
    main()