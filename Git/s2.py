# odibets_github_scraper.py (updated version)
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
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import time
import re
from datetime import datetime
import json
import logging
from pathlib import Path
import os
import sys
import traceback
import subprocess


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
        
        # Execution timeout
        self.start_time = time.time()
        self.max_execution_time = 3300  # 55 minutes
        
        # Track if we have any data
        self.has_data = False
    
    def setup_logging(self):
        """Setup logging configuration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.results_dir / f"github_scraper_{timestamp}.log"
        
        self.results_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger("OdibetsGithub")
        self.logger.info(f"Initialized scraper in mode: {self.mode}")
    
    def check_timeout(self):
        """Check if we're approaching the GitHub Actions time limit"""
        elapsed = time.time() - self.start_time
        if elapsed > self.max_execution_time:
            self.logger.warning(f"Approaching time limit ({elapsed:.0f}s), saving data and exiting")
            return True
        return False
    
    def get_chrome_version(self):
        """Get installed Chrome version"""
        try:
            result = subprocess.run(['google-chrome', '--version'], 
                                  capture_output=True, text=True)
            version = result.stdout.strip()
            self.logger.info(f"Chrome version: {version}")
            return version
        except Exception as e:
            self.logger.error(f"Failed to get Chrome version: {e}")
            return None
    
    def setup_driver(self):
        """Configure Chrome WebDriver for GitHub Actions"""
        chrome_options = Options()
        
        # Essential options for GitHub Actions
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
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--log-level=3")
        
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # Page load strategy
        chrome_options.page_load_strategy = 'normal'
        
        # Get Chrome version for debugging
        self.get_chrome_version()
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Attempting to setup Chrome driver (attempt {attempt + 1}/{max_retries})")
                
                # Try to find chromedriver in PATH
                import shutil
                chromedriver_path = shutil.which('chromedriver')
                
                if chromedriver_path:
                    self.logger.info(f"Found ChromeDriver at: {chromedriver_path}")
                    service = Service(executable_path=chromedriver_path)
                else:
                    self.logger.warning("ChromeDriver not found in PATH, trying default")
                    service = Service()
                
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                self.wait = WebDriverWait(self.driver, 20)
                self.driver.implicitly_wait(10)
                
                self.logger.info("Chrome driver initialized successfully")
                return
                
            except Exception as e:
                self.logger.error(f"Failed to initialize Chrome driver (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(5)
    
    def handle_popup(self):
        """Close popup if present"""
        try:
            time.sleep(2)
            # Try multiple selectors
            selectors = [
                ".roadblock-close button",
                ".modal-close",
                "button.close",
                "[aria-label='Close']"
            ]
            
            for selector in selectors:
                try:
                    close_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    close_button.click()
                    self.logger.info(f"Popup closed using selector: {selector}")
                    time.sleep(1)
                    return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            self.logger.debug(f"No popup found: {e}")
            return False
    
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
            if 'home' in label_lower or label == '1':
                return "First Team to Score - Home"
            elif 'away' in label_lower or label == '2':
                return "First Team to Score - Away"
            elif 'no goal' in label_lower or label == 'NG':
                return "First Team to Score - No Goal"
        
        # Total Goals
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
        
        return f"{market_name} - {label}"
    
    def scrape_goal_markets(self):
        """Scrape all goal-related markets"""
        self.logger.info("="*80)
        self.logger.info("PHASE 1: GOAL MARKETS SCRAPING")
        self.logger.info("="*80)
        
        try:
            # Wait for page to load
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".virtual-timer"))
            )
            self.logger.info("✓ Page loaded")
            
            # Close popup if present
            self.handle_popup()
            
            # Click third timestamp
            timestamp_elements = self.driver.find_elements(By.CSS_SELECTOR, '.virtual-timer .ss')
            if not timestamp_elements or len(timestamp_elements) < 3:
                self.logger.error("Not enough timestamps found")
                return None, None, None
            
            # Click the third timestamp
            third_timestamp = timestamp_elements[2]
            timestamp_text = third_timestamp.text.strip()
            self.selected_timestamp = timestamp_text
            self.logger.info(f"Clicking THIRD timestamp: {timestamp_text}")
            self.driver.execute_script("arguments[0].click();", third_timestamp)
            time.sleep(3)
            
            # Get all matches
            game_elements = self.driver.find_elements(By.CSS_SELECTOR, '.h.show .game.e')
            self.logger.info(f"✓ Found {len(game_elements)} matches")
            
            # Extract match details
            match_details = []
            for i, game in enumerate(game_elements, 1):
                try:
                    teams = game.find_elements(By.CSS_SELECTOR, '.t .t-l')
                    if len(teams) >= 2:
                        home_team = teams[0].text.strip()
                        away_team = teams[1].text.strip()
                        match_details.append({
                            'index': i,
                            'home': home_team,
                            'away': away_team,
                            'match': f"{home_team} vs {away_team}"
                        })
                except Exception as e:
                    self.logger.error(f"Error extracting match {i}: {e}")
            
            self.logger.info(f"✓ Extracted {len(match_details)} match details")
            
            # Define goal markets (simplified for GitHub Actions)
            goal_markets = {
                'GG/NG': {
                    'type': 'visible',
                    'description': 'Both Teams to Score'
                },
                'OV/UN 1.5': {
                    'type': 'dropdown',
                    'value': '1X2OU15',
                    'description': 'Over/Under 1.5 Goals'
                },
                'OV/UN 2.5': {
                    'type': 'dropdown',
                    'value': '1X2OU25',
                    'description': 'Over/Under 2.5 Goals'
                },
                'OV/UN 3.5': {
                    'type': 'dropdown',
                    'value': 'TG35',
                    'description': 'Over/Under 3.5 Goals'
                }
            }
            
            all_goal_market_data = {}
            
            # Capture GG/NG
            self.logger.info("Capturing GG/NG...")
            market_data_ggng = {}
            for game_idx, game in enumerate(game_elements):
                if game_idx >= len(match_details):
                    continue
                match_key = match_details[game_idx]['match']
                try:
                    container = game.find_element(By.CSS_SELECTOR, '.odds > .o.s-2.m2')
                    odds = []
                    buttons = container.find_elements(By.TAG_NAME, 'button')
                    for btn in buttons:
                        try:
                            label = btn.find_element(By.CSS_SELECTOR, '.o-1').text.strip()
                            value = btn.find_element(By.CSS_SELECTOR, '.o-2').text.strip()
                            if label and value:
                                odds.append({
                                    'label': label,
                                    'value': value,
                                    'selection': self.format_goal_selection('GG/NG', label)
                                })
                        except:
                            continue
                    market_data_ggng[match_key] = odds
                except:
                    market_data_ggng[match_key] = []
            
            all_goal_market_data['GG/NG'] = {
                'description': 'Both Teams to Score',
                'data': market_data_ggng
            }
            self.has_data = True
            
            # Save data immediately
            self.save_goal_markets_data(all_goal_market_data, match_details, timestamp_text)
            
            return match_details, all_goal_market_data, timestamp_text
            
        except Exception as e:
            self.logger.error(f"Error in goal markets scraping: {e}")
            traceback.print_exc()
            return None, None, None
    
    def save_goal_markets_data(self, all_goal_market_data, match_details, timestamp_text):
        """Save goal markets data to file"""
        try:
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_timestamp = timestamp_text.replace(':', '-').replace(' ', '_')
            json_filename = self.results_dir / f"goal_markets_{safe_timestamp}_{timestamp_str}.json"
            
            structured_data = {
                'scrape_timestamp': datetime.now().isoformat(),
                'timestamp_clicked': timestamp_text,
                'total_matches': len(match_details),
                'markets': {},
                'matches': match_details
            }
            
            for market_name, market_info in all_goal_market_data.items():
                structured_data['markets'][market_name] = {
                    'description': market_info['description'],
                    'odds': {}
                }
                for match_key, odds in market_info['data'].items():
                    if odds:
                        structured_data['markets'][market_name]['odds'][match_key] = odds
            
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"✓ Goal markets saved to: {json_filename}")
        except Exception as e:
            self.logger.error(f"Error saving goal markets data: {e}")
    
    def get_prematch_timer(self):
        """Get pre-match timer if visible"""
        try:
            timer_element = self.driver.find_element(By.CSS_SELECTOR, ".countdown.pre.show .bnt")
            timer_text = timer_element.text.strip()
            
            if not timer_text:
                return None
                
            if timer_text.isdigit():
                seconds = int(timer_text)
                if seconds < 60:
                    return f"00:{seconds:02d}"
                else:
                    minutes = seconds // 60
                    secs = seconds % 60
                    return f"{minutes:02d}:{secs:02d}"
            
            return timer_text
            
        except NoSuchElementException:
            return None
        except Exception:
            return None
    
    def get_live_minutes(self):
        """Get the live match minutes from the live tab"""
        try:
            live_tab = self.driver.find_element(By.CSS_SELECTOR, ".tbs li.live.active")
            try:
                minutes_span = live_tab.find_element(By.CSS_SELECTOR, "span")
                return minutes_span.text.strip()
            except:
                return "LIVE"
        except NoSuchElementException:
            return None
        except Exception:
            return None
    
    def get_live_matches(self):
        """Get all live matches with scores"""
        matches = []
        try:
            match_elements = self.driver.find_elements(By.CSS_SELECTOR, ".play.show .gm")
            
            for match in match_elements:
                try:
                    home = match.find_element(By.CSS_SELECTOR, ".t-1-j").text
                    away = match.find_element(By.CSS_SELECTOR, ".t-2-j").text
                    
                    scores = match.find_elements(By.CSS_SELECTOR, ".s .d")
                    home_score = scores[0].text if scores else "0"
                    away_score = scores[1].text if len(scores) > 1 else "0"
                    
                    goals = match.find_elements(By.CSS_SELECTOR, ".hi span")
                    goal_times = [g.text for g in goals]
                    
                    matches.append({
                        'home': home,
                        'away': away,
                        'home_score': home_score,
                        'away_score': away_score,
                        'goal_times': goal_times
                    })
                except:
                    continue
        except:
            pass
        return matches
    
    def monitor_timer(self, match_details):
        """Monitor the timer for the selected timestamp"""
        self.logger.info("="*80)
        self.logger.info("PHASE 2: TIMER MONITORING")
        self.logger.info("="*80)
        
        self.logger.info(f"Monitoring timer for: {self.selected_timestamp}")
        
        consecutive_zero_checks = 0
        zero_threshold = 3
        check_count = 0
        max_checks = 600  # 5 minutes max monitoring (0.5s * 600 = 300s)
        
        while not self.timer_reached_zero and check_count < max_checks:
            check_count += 1
            pre_timer = self.get_prematch_timer()
            
            if pre_timer:
                if pre_timer != self.current_pre_timer:
                    self.current_pre_timer = pre_timer
                    self.logger.info(f"⏱️ Pre-match: {pre_timer}")
                
                # Check for zero
                is_zero = (
                    pre_timer in ["00:00", "0:00", "0"] or
                    (pre_timer.isdigit() and int(pre_timer) == 0)
                )
                
                if is_zero:
                    consecutive_zero_checks += 1
                    if consecutive_zero_checks >= zero_threshold:
                        self.timer_reached_zero = True
                        self.kickoff_time = datetime.now().strftime("%H:%M:%S")
                        self.logger.info(f"⚡ TIMER REACHED ZERO")
                        return True
                else:
                    consecutive_zero_checks = 0
            
            if self.check_timeout():
                return False
            
            time.sleep(0.5)
        
        if check_count >= max_checks:
            self.logger.warning("Timer monitoring timed out")
        
        return self.timer_reached_zero
    
    def check_goals(self, live_matches):
        """Check for new goals and alert"""
        for match in live_matches:
            match_key = f"{match['home']} vs {match['away']}"
            current_score = f"{match['home_score']}-{match['away_score']}"
            
            if not match['home_score'].isdigit() or not match['away_score'].isdigit():
                continue
                
            current_home = int(match['home_score'])
            current_away = int(match['away_score'])
            
            if match_key in self.previous_scores:
                prev_score = self.previous_scores[match_key]
                
                if '-' not in prev_score:
                    self.previous_scores[match_key] = current_score
                    continue
                    
                try:
                    prev_home = int(prev_score.split('-')[0])
                    prev_away = int(prev_score.split('-')[1])
                except:
                    self.previous_scores[match_key] = current_score
                    continue
                
                if current_home != prev_home or current_away != prev_away:
                    self.goal_count += 1
                    
                    if current_home > prev_home:
                        scorer = match['home']
                    else:
                        scorer = match['away']
                    
                    minute = match['goal_times'][-1] if match['goal_times'] else '?'
                    
                    self.logger.info(f"⚽ GOAL #{self.goal_count} - {scorer} ({minute})")
                    self.logger.info(f"   {match_key}: {prev_score} → {current_score}")
                    self.has_data = True
            
            self.previous_scores[match_key] = current_score
    
    def track_live_matches(self):
        """Track live matches and goals"""
        self.logger.info("="*80)
        self.logger.info("PHASE 3: LIVE MATCH TRACKING")
        self.logger.info("="*80)
        
        self.logger.info("Waiting for live matches...")
        
        # Wait for live transition
        live_wait_start = time.time()
        live_ready = False
        
        while time.time() - live_wait_start < 30:
            if self.get_live_minutes() or self.get_live_matches():
                live_ready = True
                break
            time.sleep(1)
            
            if self.check_timeout():
                return False
        
        if not live_ready:
            self.logger.warning("No live matches detected")
            return False
        
        time.sleep(2)
        
        self.logger.info("🟢 Live matches in progress")
        
        # Create live tracking file
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        live_log_file = self.results_dir / f"live_tracking_{timestamp_str}.json"
        live_data = {
            'start_time': datetime.now().isoformat(),
            'selected_timestamp': self.selected_timestamp,
            'kickoff_time': self.kickoff_time,
            'goals': []
        }
        
        # Monitoring loop
        max_live_time = 1800  # 30 minutes max live tracking
        live_start = time.time()
        
        while self.live_mode_active and (time.time() - live_start) < max_live_time:
            live_minutes = self.get_live_minutes()
            live_matches = self.get_live_matches()
            
            if live_minutes and live_minutes != self.current_live_timer:
                self.current_live_timer = live_minutes
                self.logger.info(f"🟢 Live: {live_minutes}")
            
            if live_matches:
                self.check_goals(live_matches)
            
            # Check if matches have ended
            try:
                active_tab = self.driver.find_element(By.CSS_SELECTOR, ".tbs li.active")
                if active_tab.text.strip() == 'Results':
                    self.logger.info("All matches ended")
                    self.live_mode_active = False
                    break
            except:
                pass
            
            if self.check_timeout():
                break
            
            time.sleep(2)  # Check every 2 seconds to reduce resource usage
        
        # Save live tracking data
        live_data['end_time'] = datetime.now().isoformat()
        live_data['total_goals'] = self.goal_count
        
        with open(live_log_file, 'w', encoding='utf-8') as f:
            json.dump(live_data, f, indent=2)
        self.logger.info(f"Live tracking saved to {live_log_file}")
        
        return True
    
    def navigate_to_tab(self, tab_name):
        """Navigate to specific tab"""
        try:
            self.logger.info(f"Navigating to {tab_name} tab")
            
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ul.tbs"))
            )
            
            tab = self.driver.find_element(By.XPATH, f"//ul[@class='tbs']//li[contains(text(), '{tab_name}')]")
            tab.click()
            time.sleep(3)
            return True
            
        except Exception as e:
            self.logger.error(f"Error navigating to {tab_name}: {e}")
            return False
    
    def scrape_standings(self):
        """Scrape standings data"""
        try:
            self.logger.info("Scraping standings...")
            
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.virtual-standings"))
            )
            
            # Get season title
            try:
                season_element = self.driver.find_element(By.CSS_SELECTOR, "div.virtual-standings div.title")
                season_title = season_element.text.strip()
            except:
                season_title = "Unknown Season"
            
            # Get all team rows
            rows = self.driver.find_elements(By.CSS_SELECTOR, "div.virtual-standings table tbody tr")
            
            standings_data = []
            for row in rows:
                cells = row.find_elements(By.CSS_SELECTOR, "td")
                if len(cells) >= 4:
                    position = cells[0].text.strip()
                    team = cells[1].text.strip()
                    points = cells[2].text.strip()
                    
                    # Get form
                    form_cell = cells[3]
                    form_items = form_cell.find_elements(By.CSS_SELECTOR, "div")
                    
                    form_results = []
                    for item in form_items:
                        form_text = item.text.strip()
                        if form_text:
                            form_results.append(form_text)
                    
                    form_string = "".join(form_results)
                    form_spaced = " ".join(form_results)
                    
                    wins = sum(1 for f in form_results if f == "W")
                    draws = sum(1 for f in form_results if f == "D")
                    losses = sum(1 for f in form_results if f == "L")
                    
                    standings_data.append({
                        "position": int(position) if position.isdigit() else 0,
                        "team": team,
                        "points": int(points) if points.isdigit() else 0,
                        "form": {
                            "results": form_results,
                            "form_string": form_string,
                            "form_spaced": form_spaced,
                            "wins": wins,
                            "draws": draws,
                            "losses": losses
                        }
                    })
            
            result = {
                "season": season_title,
                "teams": standings_data,
                "total_teams": len(standings_data)
            }
            
            self.has_data = True
            return result
            
        except Exception as e:
            self.logger.error(f"Error scraping standings: {e}")
            return None
    
    def scrape_results(self):
        """Scrape results data"""
        try:
            self.logger.info("Scraping results...")
            
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.virtual-rs"))
            )
            
            result_blocks = self.driver.find_elements(By.CSS_SELECTOR, "div.rs")
            self.logger.info(f"Found {len(result_blocks)} result weeks")
            
            results_data = []
            
            for block_index, block in enumerate(result_blocks[:3], 1):  # Limit to 3 weeks
                try:
                    # Get week header
                    week_header = block.find_element(By.CSS_SELECTOR, "div.rs-t")
                    week_title = week_header.find_element(By.CSS_SELECTOR, "div.t").text.strip()
                    week_time = week_header.find_element(By.CSS_SELECTOR, "div.b").text.strip()
                    
                    # Get games
                    games = block.find_elements(By.CSS_SELECTOR, "div.rs-g")
                    
                    week_data = {
                        "week_number": block_index,
                        "week_title": week_title,
                        "time": week_time,
                        "games": []
                    }
                    
                    for game in games:
                        try:
                            teams = game.find_elements(By.CSS_SELECTOR, "div.g-t")
                            if len(teams) >= 2:
                                home_team = teams[0].text.strip()
                                away_team = teams[1].text.strip()
                                
                                scores = game.find_elements(By.CSS_SELECTOR, "div.g-s span")
                                if len(scores) >= 2:
                                    home_score = scores[0].text.strip()
                                    away_score = scores[1].text.strip()
                                    
                                    game_data = {
                                        "home_team": home_team,
                                        "away_team": away_team,
                                        "home_score": int(home_score) if home_score.isdigit() else 0,
                                        "away_score": int(away_score) if away_score.isdigit() else 0,
                                        "full_time": f"{home_score}-{away_score}"
                                    }
                                    week_data["games"].append(game_data)
                        except:
                            continue
                    
                    if week_data["games"]:
                        results_data.append(week_data)
                    
                except Exception as e:
                    self.logger.error(f"Error processing week {block_index}: {e}")
                    continue
            
            result = {
                "total_weeks": len(results_data),
                "total_games": sum(len(week['games']) for week in results_data),
                "weeks": results_data
            }
            
            self.has_data = True
            return result
            
        except Exception as e:
            self.logger.error(f"Error scraping results: {e}")
            return None
    
    def scrape_results_and_standings(self):
        """Scrape both results and standings"""
        self.logger.info("="*80)
        self.logger.info("PHASE 4: RESULTS & STANDINGS")
        self.logger.info("="*80)
        
        results_data = None
        standings_data = None
        
        # Scrape Results
        if self.navigate_to_tab("Results"):
            results_data = self.scrape_results()
            if results_data:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                results_file = self.results_dir / f"results_{timestamp}.json"
                with open(results_file, 'w', encoding='utf-8') as f:
                    json.dump(results_data, f, indent=2)
                self.logger.info(f"Results saved to {results_file}")
        
        time.sleep(2)
        
        # Scrape Standings
        if self.navigate_to_tab("Standings"):
            standings_data = self.scrape_standings()
            if standings_data:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                standings_file = self.results_dir / f"standings_{timestamp}.json"
                with open(standings_file, 'w', encoding='utf-8') as f:
                    json.dump(standings_data, f, indent=2)
                self.logger.info(f"Standings saved to {standings_file}")
        
        return results_data, standings_data
    
    def save_summary(self, results):
        """Save execution summary"""
        summary_file = self.results_dir / f"execution_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        summary = {
            'execution_time': datetime.now().isoformat(),
            'mode': self.mode,
            'results': results,
            'timestamp_selected': self.selected_timestamp,
            'goals_detected': self.goal_count,
            'has_data': self.has_data
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
    
    def run(self):
        """Main execution flow"""
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
            
            results = {}
            
            # Execute based on mode
            if self.mode in ['full', 'goals_only']:
                self.logger.info("Starting goal markets scraping...")
                match_details, goal_markets_data, timestamp_text = self.scrape_goal_markets()
                results['goal_markets'] = {
                    'success': match_details is not None,
                    'timestamp': timestamp_text
                }
                
                if self.check_timeout():
                    self.save_summary(results)
                    return
            
            if self.mode in ['full', 'live_only'] and self.mode != 'goals_only':
                if self.mode == 'full' and 'match_details' in locals() and match_details:
                    self.logger.info("Starting timer monitoring...")
                    self.monitor_timer(match_details)
                    
                    if self.check_timeout():
                        self.save_summary(results)
                        return
                    
                    self.logger.info("Starting live tracking...")
                    self.track_live_matches()
                    results['live_tracking'] = {
                        'goals_detected': self.goal_count,
                        'kickoff_time': self.kickoff_time
                    }
            
            if self.mode in ['full', 'results_only']:
                self.logger.info("Starting results & standings scraping...")
                time.sleep(5)
                results_data, standings_data = self.scrape_results_and_standings()
                results['results_standings'] = {
                    'results_success': results_data is not None,
                    'standings_success': standings_data is not None
                }
            
            # Save summary
            self.save_summary(results)
            
            total_time = time.time() - overall_start
            self.logger.info("="*80)
            self.logger.info(f"✅ SCRAPING COMPLETED in {total_time:.2f} seconds")
            self.logger.info(f"   Data saved in: {self.results_dir}")
            self.logger.info("="*80)
            
        except Exception as e:
            self.logger.error(f"Error in main execution: {e}")
            traceback.print_exc()
            self.save_error_log(str(e))
        finally:
            if self.driver:
                self.driver.quit()
                self.logger.info("Browser closed")


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
        try:
            scraper.save_error_log(str(e))
        except:
            pass
    finally:
        print("\n" + "="*80)
        print("✅ Script finished")
        print("="*80 + "\n")


if __name__ == "__main__":
    main()
