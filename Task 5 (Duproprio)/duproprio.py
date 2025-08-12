import time
import csv
import json
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import gspread
from google.oauth2.service_account import Credentials

class DuProprioScraper:
    def __init__(self, email, password, google_sheets_creds_path=None):
        self.email = email
        self.password = password
        self.google_sheets_creds_path = google_sheets_creds_path
        self.driver = None
        self.wait = None
        self.properties_data = []
        
    def setup_driver(self, headless=False):
        """Setup Chrome WebDriver with options"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-logging")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # Disable notifications and popups
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.default_content_settings.popups": 0
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.maximize_window()
        self.wait = WebDriverWait(self.driver, 30)
        
    def take_screenshot(self, filename):
        """Take screenshot for debugging"""
        try:
            self.driver.save_screenshot(filename)
            print(f"Screenshot saved: {filename}")
        except Exception as e:
            print(f"Failed to take screenshot: {e}")
        
    def login(self):
        """Login to DuProprio account - converted from working Playwright code"""
        try:
            print('Navigating to login page...')
            self.driver.get('https://auth.duproprio.com/?lng=en')
            time.sleep(3)
            
            # Take screenshot for debugging
            self.take_screenshot('login_page.png')
            
            # Debug: Log current URL and page title
            print('Current URL:', self.driver.current_url)
            print('Page title:', self.driver.title)
            
            # Try multiple possible selectors for the email field
            email_selectors = [
                '#text-email',
                'input[type="email"]',
                'input[name="email"]',
                'input[placeholder*="email"]',
                'input[id*="email"]'
            ]
            
            email_input = None
            used_selector = ''
            
            for selector in email_selectors:
                try:
                    email_input = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    used_selector = selector
                    print(f'Found email input with selector: {selector}')
                    break
                except TimeoutException:
                    print(f'Selector {selector} not found')
                    continue
            
            if not email_input:
                # Debug: Get available input fields
                inputs = self.driver.find_elements(By.TAG_NAME, "input")
                print("Available input fields:")
                for i, inp in enumerate(inputs):
                    print(f"Input {i}: type='{inp.get_attribute('type')}', name='{inp.get_attribute('name')}', id='{inp.get_attribute('id')}', placeholder='{inp.get_attribute('placeholder')}'")
                raise Exception('Could not find email input field with any known selector')
            
            # Fill email
            print('Filling email...')
            email_input.clear()
            email_input.send_keys(self.email)
            
            # Look for continue/submit button
            continue_selectors = [
                'button[type="submit"]',
                'button:contains("Continue")',
                'button:contains("Continuer")', 
                'input[type="submit"]',
                '.btn-primary',
                '[data-testid="continue-button"]'
            ]
            
            continue_button = None
            for selector in continue_selectors:
                try:
                    if ':contains(' in selector:
                        # Convert CSS :contains to XPath
                        text = selector.split(':contains("')[1].split('")')[0]
                        xpath_selector = f'//button[contains(text(), "{text}")]'
                        continue_button = self.driver.find_element(By.XPATH, xpath_selector)
                    else:
                        continue_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if continue_button and continue_button.is_displayed():
                        print(f'Found continue button with selector: {selector}')
                        continue_button.click()
                        break
                except (NoSuchElementException, WebDriverException):
                    print(f'Continue button selector {selector} not found')
                    continue
            
            if not continue_button:
                raise Exception('Could not find continue button')
            
            # Wait for next step
            time.sleep(5)
            
            # Fill password
            print('Looking for password field...')
            password_selectors = [
                '#password-password',
                'input[type="password"]',
                'input[name="password"]',
                'input[placeholder*="password"]'
            ]
            
            password_input = None
            password_selector = ''
            
            for selector in password_selectors:
                try:
                    password_input = self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    password_selector = selector
                    print(f'Found password input with selector: {selector}')
                    break
                except TimeoutException:
                    print(f'Password selector {selector} not found')
                    continue
            
            if not password_input:
                self.take_screenshot('password_page.png')
                raise Exception('Could not find password input field')
            
            password_input.clear()
            password_input.send_keys(self.password)
            
            # Look for sign in button
            signin_selectors = [
                'button[type="submit"]',
                '//button[contains(text(), "Sign in")]',
                '//button[contains(text(), "Se connecter")]',
                '//button[contains(text(), "Log in")]',
                '.btn-primary',
                'input[type="submit"]',
                '//button[contains(text(), "Connect")]',
                '//button[contains(text(), "Connexion")]'
            ]
            
            signin_button = None
            for selector in signin_selectors:
                try:
                    if selector.startswith('//'):
                        signin_button = self.driver.find_element(By.XPATH, selector)
                    else:
                        signin_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    
                    if signin_button and signin_button.is_displayed():
                        print(f'Found signin button with selector: {selector}')
                        signin_button.click()
                        print('Clicked signin button')
                        break
                except (NoSuchElementException, WebDriverException):
                    print(f'Signin button selector {selector} not found')
                    continue
            
            if not signin_button:
                self.take_screenshot('password_page_no_button.png')
                raise Exception('Could not find signin button')
            
            # Wait for navigation after login
            print('Waiting for login to complete...')
            time.sleep(5)
            
            current_url = self.driver.current_url
            print('Login process completed. Current URL:', current_url)
            
            # Check if login was successful
            if 'auth.duproprio.com' in current_url:
                self.take_screenshot('login_failed.png')
                
                # Check for error messages
                try:
                    error_elements = self.driver.find_elements(By.CSS_SELECTOR, '[class*="error"], .alert-danger, .text-danger')
                    if error_elements:
                        error_messages = [elem.text.strip() for elem in error_elements if elem.text.strip()]
                        print('Login error messages:', error_messages)
                except:
                    pass
                
                raise Exception(f'Login failed - still on login page: {current_url}')
            
            self.take_screenshot('after_login.png')
            print("Login successful!")
            
        except Exception as e:
            print(f"Login failed: {e}")
            raise
            
    def navigate_to_favorites(self):
        """Navigate to favorites page with retry logic"""
        print('Navigating to favorites...')
        
        favorites_page_loaded = False
        retry_count = 0
        max_retries = 3
        
        while not favorites_page_loaded and retry_count < max_retries:
            try:
                retry_count += 1
                print(f'Attempt {retry_count}/{max_retries} to load favorites page...')
                
                self.driver.get('https://duproprio.com/en/mdp/visitor/favourites')
                time.sleep(8)
                
                current_url = self.driver.current_url
                print(f'Current URL after navigation attempt: {current_url}')
                
                if 'favourites' in current_url or 'favorites' in current_url:
                    favorites_page_loaded = True
                    print('Successfully loaded favorites page')
                elif 'auth' in current_url or 'login' in current_url:
                    raise Exception('Redirected to login page - session might have expired')
                else:
                    print('Unexpected page loaded, will retry...')
                    time.sleep(3)
                    
            except Exception as e:
                print(f'Attempt {retry_count} failed:', str(e))
                if retry_count >= max_retries:
                    print('All attempts failed, trying alternative approach...')
                    
                    # Try navigating to main account page first
                    try:
                        print('Trying to navigate to main account page first...')
                        self.driver.get('https://duproprio.com/en/mdp')
                        time.sleep(5)
                        
                        # Then try to click on favorites link
                        favorites_link_selectors = [
                            'a[href*="favourites"]',
                            '//a[contains(text(), "My favourites")]',
                            '//a[contains(text(), "Mes favoris")]'
                        ]
                        
                        for selector in favorites_link_selectors:
                            try:
                                if selector.startswith('//'):
                                    favorites_link = self.driver.find_element(By.XPATH, selector)
                                else:
                                    favorites_link = self.driver.find_element(By.CSS_SELECTOR, selector)
                                
                                if favorites_link:
                                    print('Found favorites link, clicking...')
                                    favorites_link.click()
                                    time.sleep(5)
                                    favorites_page_loaded = True
                                    break
                            except:
                                continue
                                
                        if not favorites_page_loaded:
                            raise Exception('Could not find favorites link on account page')
                            
                    except Exception as alt_error:
                        print('Alternative navigation also failed:', str(alt_error))
                        raise Exception(f'Failed to load favorites page after {max_retries} attempts and alternative method')
                else:
                    time.sleep(3)
        
        # Take screenshot after successful load
        self.take_screenshot('favorites_loaded.png')
        
        # Wait for content to load
        print('Waiting for favorites content to load...')
        time.sleep(10)  # Reduced from 120 to 10 seconds

    def get_all_property_links(self):
        """Extract all property links from all pages in favorites"""
        print('Starting to extract all property links with pagination...')
        all_property_links = []
        current_page = 1
        max_pages = 100  # Safety limit, adjust based on your needs
        
        while current_page <= max_pages:
            print(f'\n--- Processing page {current_page} ---')
            
            # Get property links from current page
            page_links = self.get_property_links_from_current_page()
            
            if page_links:
                all_property_links.extend(page_links)
                print(f'Found {len(page_links)} properties on page {current_page}')
                print(f'Total properties found so far: {len(all_property_links)}')
            else:
                print(f'No properties found on page {current_page}')
            
            # Check if there's a next page and navigate to it
            if not self.go_to_next_page():
                print('No more pages available or failed to navigate to next page')
                break
                
            current_page += 1
            time.sleep(3)  # Brief pause between pages
        
        # Remove duplicates
        unique_links = list(set(all_property_links))
        print(f'\nCompleted pagination! Found {len(unique_links)} unique property links total')
        
        return unique_links
        
    def get_property_links_from_current_page(self):
        """Extract property links from the current page only"""
        print('Extracting property links from current page...')
        
        # Wait for page content to load
        time.sleep(5)
        
        # Property selectors based on your working code and HTML structure
        property_selectors = [
            'a[data-testid="favourite-card"]',  # Primary selector from your HTML
            'a[href*="/en/"][data-testid="favourite-card"]',
            'a.sc-fkxiEW[href*="duproprio.com/en/"]',
            'a[href*="duproprio.com/en/"]'
        ]
        
        property_links = []
        
        for selector in property_selectors:
            try:
                print(f'Trying selector: {selector}')
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                
                for element in elements:
                    href = element.get_attribute('href')
                    if href and 'duproprio.com/en/' in href and '/en/' in href:
                        # Extract the property ID pattern (e.g., /en/1110325)
                        if any(char.isdigit() for char in href):
                            property_links.append(href)
                
                if len(property_links) > 0:
                    print(f'Found {len(property_links)} properties with selector: {selector}')
                    break
                    
            except Exception as e:
                print(f'Property selector {selector} didn\'t work:', str(e))
                continue
        
        # Remove duplicates from this page
        property_links = list(set(property_links))
        
        if len(property_links) == 0:
            print('No property links found on current page. Debugging...')
            self.debug_current_page()
        
        return property_links
        
    def go_to_next_page(self):
        """Navigate to the next page of favorites"""
        print('Looking for next page button...')
        
        # Selectors for next page button based on typical pagination patterns
        next_page_selectors = [
            '//button[contains(@aria-label, "Next")]',
            '//button[contains(text(), "Next")]',
            '//a[contains(text(), "Next")]',
            '.pagination .next',
            'button[aria-label*="next"]',
            'a[aria-label*="next"]',
            '//button[@aria-label="Go to next page"]',
            '//a[@aria-label="Go to next page"]',
            '//button[contains(@class, "next")]',
            '//a[contains(@class, "next")]',
            # Generic pagination selectors
            '.pagination button:last-child',
            '.pagination a:last-child',
            '//nav//button[last()]',
            '//nav//a[last()]'
        ]
        
        for selector in next_page_selectors:
            try:
                if selector.startswith('//'):
                    next_button = self.driver.find_element(By.XPATH, selector)
                else:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                
                if next_button and next_button.is_displayed() and next_button.is_enabled():
                    # Check if button is not disabled
                    disabled = next_button.get_attribute('disabled')
                    aria_disabled = next_button.get_attribute('aria-disabled')
                    
                    if not disabled and aria_disabled != 'true':
                        print(f'Found and clicking next page button with selector: {selector}')
                        # Scroll to button first
                        self.driver.execute_script("arguments[0].scrollIntoView();", next_button)
                        time.sleep(1)
                        next_button.click()
                        
                        # Wait for page to load
                        time.sleep(5)
                        return True
                    else:
                        print(f'Next button found but disabled with selector: {selector}')
                        
            except (NoSuchElementException, WebDriverException) as e:
                print(f'Next page selector {selector} not found: {str(e)}')
                continue
        
        # If no next button found, try to find page numbers and click the next one
        print('No next button found, trying to find page numbers...')
        try:
            # Look for page number buttons
            page_buttons = self.driver.find_elements(By.CSS_SELECTOR, '.pagination button, .pagination a')
            current_page_text = None
            
            for button in page_buttons:
                if 'active' in button.get_attribute('class') or 'current' in button.get_attribute('class'):
                    current_page_text = button.text.strip()
                    break
            
            if current_page_text and current_page_text.isdigit():
                next_page_num = str(int(current_page_text) + 1)
                next_page_button = None
                
                for button in page_buttons:
                    if button.text.strip() == next_page_num:
                        next_page_button = button
                        break
                
                if next_page_button and next_page_button.is_displayed():
                    print(f'Found next page button for page {next_page_num}')
                    self.driver.execute_script("arguments[0].scrollIntoView();", next_page_button)
                    time.sleep(1)
                    next_page_button.click()
                    time.sleep(5)
                    return True
                    
        except Exception as e:
            print(f'Error trying page numbers approach: {str(e)}')
        
        print('Could not find or click next page button')
        return False
        
    def debug_current_page(self):
        """Debug current page to understand structure"""
        print('Debugging current page structure...')
        try:
            # Take screenshot
            self.take_screenshot(f'debug_page_{int(time.time())}.png')
            
            # Get all links for debugging
            all_links = self.driver.find_elements(By.TAG_NAME, 'a')
            debug_links = []
            for link in all_links[:10]:  # First 10 for debugging
                href = link.get_attribute('href')
                text = link.text.strip()
                classes = link.get_attribute('class')
                data_testid = link.get_attribute('data-testid')
                if href:
                    debug_links.append({
                        'href': href, 
                        'text': text,
                        'classes': classes,
                        'data-testid': data_testid
                    })
            
            print('Sample links found on current page:')
            for link in debug_links:
                print(f"  - {link}")
                
        except Exception as e:
            print(f'Could not debug current page: {str(e)}')
    
    def get_all_property_links_main(self):
        """Main method to get all property links"""
        try:
            self.setup_driver(headless=False)  # Keep visible for debugging
            self.login()
            self.navigate_to_favorites()
            
            # Get all property links with pagination
            all_links = self.get_all_property_links()
            
            print(f"\nTotal unique property links found: {len(all_links)}")
            
            # Save links to file for reference
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"property_links_{timestamp}.txt"
            
            with open(filename, 'w') as f:
                for link in all_links:
                    f.write(link + '\n')
            
            print(f"Links saved to {filename}")
            
            return all_links
            
        except Exception as e:
            print(f"Error getting property links: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if self.driver:
                self.driver.quit()

def main():
    # Configuration
    EMAIL = "lisimmo4@gmail.com"
    PASSWORD = "Bleury1072*"
    
    # Initialize scraper
    scraper = DuProprioScraper(EMAIL, PASSWORD)
    
    try:
        # Get all property links
        all_links = scraper.get_all_property_links_main()
        
        if all_links:
            print(f"\nSuccessfully extracted {len(all_links)} property links!")
            print("Sample links:")
            for i, link in enumerate(all_links[:5]):  # Show first 5
                print(f"  {i+1}. {link}")
            if len(all_links) > 5:
                print(f"  ... and {len(all_links) - 5} more links")
        else:
            print("\nNo property links found. Check the debug output above.")
            
    except Exception as e:
        print(f"Main execution error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()