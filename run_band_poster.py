import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains  # 추가된 import
from selenium.webdriver.common.keys import Keys  # 추가된 import
import time
import json
import requests
from bs4 import BeautifulSoup

def setup_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Chrome 프로필 설정
    script_dir = os.path.dirname(os.path.abspath(__file__))
    profile_path = os.path.join(script_dir, 'chrome_profile')
    if os.path.exists(profile_path):
        options.add_argument(f'--user-data-dir={profile_path}')
        print("Chrome profile loaded")
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    
    # 저장된 쿠키 로드
    cookies_path = os.path.join(script_dir, 'band_cookies.json')
    if (os.path.exists(cookies_path)):
        driver.get('https://band.us')
        with open(cookies_path, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except:
                    continue
        print("Cookies loaded")
        driver.refresh()
    
    return driver

def get_url_content(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # meta 태그에서 description 추출
        description = soup.find('meta', {'name': 'description'})
        if (description):
            return description.get('content', '')
        
        # 본문 텍스트 추출
        paragraphs = soup.find_all('p')
        content = ' '.join([p.get_text() for p in paragraphs])
        return content.strip()
        
    except Exception as e:
        print(f"URL 내용 가져오기 실패: {str(e)}")
        return url

def login(driver, config):
    try:
        print("\n=== 로그인 시도 시작 ===")
        driver.get('https://auth.band.us/login')
        time.sleep(3)
        
        # 이메일 로그인 버튼 클릭 전에 출력
        print("⭐ 로그인 시도 중...")
        
        # 이메일 로그인 버튼 클릭
        email_login_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '.uButtonRound.-h56.-icoType.-email'))
        )
        email_login_btn.click()
        
        # 이메일 입력
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'input_email'))
        )
        email_input.send_keys(config['email'])
        
        email_confirm_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '.uBtn.-tcType.-confirm'))
        )
        email_confirm_btn.click()
        
        # 비밀번호 입력
        pw_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'pw'))
        )
        pw_input.send_keys(config['password'])
        
        pw_confirm_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, '.uBtn.-tcType.-confirm'))
        )
        pw_confirm_btn.click()
        
        # 2차 인증 처리
        try:
            verification_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, 'code'))
            )
            verification_code = input("이메일로 받은 인증 코드를 입력해주세요: ")
            verification_input.send_keys(verification_code)
            
            verify_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.uBtn.-tcType.-confirm'))
            )
            verify_btn.click()
            time.sleep(5)
        except:
            pass
        
        # 로그인 성공 후 메인 페이지 로딩 대기
        WebDriverWait(driver, 30).until(
            EC.url_to_be("https://band.us/")
        )
        print("✅ 로그인 완료!")
        print("=== 로그인 프로세스 종료 ===\n")
        
    except Exception as e:
        print(f"❌ 로그인 실패: {str(e)}")
        raise e

def post_to_band(driver, config, band_info):
    try:
        # 밴드로 이동
        driver.get(band_info['url'])
        time.sleep(5)
        
        # 글쓰기 버튼 찾기
        write_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button._btnPostWrite'))
        )
        print("글쓰기 버튼 발견")
        driver.execute_script("arguments[0].click();", write_btn)
        time.sleep(2)
        
        # 글 작성
        editor = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[contenteditable="true"]'))
        )
        
        # 포스팅 URL의 내용 가져오기
        post_url = config['post_url']
        content = get_url_content(post_url)
        
        # 제목 입력
        title = config['title']
        if (title):
            editor.send_keys(title)
            ActionChains(driver).send_keys(Keys.ENTER).perform()
            time.sleep(1)
        print(f"URL 입력 시작: {post_url}")
        
        # 에디터 클릭 및 URL 붙여넣기
        editor.click()
        editor.clear()  # 기존 내용 클리어
        editor.send_keys(post_url)
        time.sleep(1)
        print("URL 입력 및 엔터 완료")
        
        ActionChains(driver).send_keys(Keys.ENTER).perform()
        print("미리보기 로딩 대기 중 (600초)...")
        time.sleep(600)
        
        # URL 텍스트 삭제
        editor.click()
        
        # JavaScript로 정확한 URL 텍스트만 삭제
        driver.execute_script("""
            var editor = arguments[0];
            var url = arguments[1];
            
            // 현재 내용에서 URL 텍스트만 찾아서 삭제
            editor.innerHTML = editor.innerHTML.replace(url, '');
            // 줄바꿈 문자도 삭제
            editor.innerHTML = editor.innerHTML.replace(/^\\n|\\n$/g, '');
            editor.innerHTML = editor.innerHTML.trim();
            
            // 변경 이벤트 발생
            editor.dispatchEvent(new Event('input', { bubbles: true }));
        """, editor, post_url)
        
        # 게시 버튼 클릭
        submit_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.uButton.-sizeM._btnSubmitPost.-confirm'))
        )
        time.sleep(3)
        submit_btn.click()
        
        # 게시판 선택 팝업 처리
        try:
            # 팝업 헤더 확인
            popup_header = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'header.modalHeader'))
            )
            
            if "게시판 선택" in popup_header.text:
                print("게시판 선택 팝업 감지됨")
                
                # 첫 번째 flexList 요소 찾기 및 클릭
                first_flex_list = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'label.flexList'))
                )
                first_flex_list.click()
                print("첫 번째 게시판 선택됨")
                
                # 확인 버튼 클릭
                confirm_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.uButton.-confirm._btnConfirm'))
                )
                confirm_btn.click()
                print("게시판 선택 확인")
                
                # 최종 게시 버튼 클릭
                final_submit_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.uButton.-sizeM._btnSubmitPost.-confirm'))
                )
                time.sleep(2)
                final_submit_btn.click()
                print("최종 게시 완료")
        except Exception as e:
            print(f"게시판 선택 처리 중 오류 (무시됨): {str(e)}")

        print("게시 완료")
        time.sleep(3)
        
        print("\n포스팅 완료!")
        return True
        
    except Exception as e:
        print(f"포스팅 실패: {str(e)}")
        return False

def normal_posting_process(driver, config):
    """일반적인 포스팅 프로세스"""
    try:
        # 로그인
        login(driver, config)
        
        # 밴드 목록 가져오기
        driver.get('https://band.us/feed')
        time.sleep(5)  # 페이지 로딩 대기 시간 증가
        
        # "내 밴드 더보기" 버튼 찾고 클릭 (반드시 실행)
        try:
            # 더보기 버튼이 보일 때까지 스크롤
            for _ in range(3):  # 최대 3번 시도
                try:
                    more_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.myBandMoreView._btnMore'))
                    )
                    driver.execute_script("arguments[0].scrollIntoView(true);", more_btn)
                    time.sleep(2)
                    more_btn.click()
                    print("내 밴드 더보기 버튼 클릭 성공")
                    time.sleep(3)  # 목록 로딩 대기
                    break
                except:
                    # 스크롤 다운
                    driver.execute_script("window.scrollBy(0, 300);")
                    time.sleep(1)
        except Exception as e:
            print(f"더보기 버튼 클릭 실패: {str(e)}")
            return 1

        # 밴드 목록 로드 대기
        band_list = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'ul[data-viewname="DMyGroupBandBannerView.MyGroupBandListView"]'))
        )
        
        # 모든 밴드 항목 찾기
        band_items = band_list.find_elements(By.CSS_SELECTOR, 'li[data-viewname="DMyGroupBandListItemView"]')
        band_elements = []
        
        for item in band_items:
            try:
                band_link = item.find_element(By.CSS_SELECTOR, 'a.itemMyBand')
                band_name = item.find_element(By.CSS_SELECTOR, 'span.body strong.ellipsis').text.strip()
                band_url = band_link.get_attribute('href')
                
                if (band_url and band_name):
                    band_elements.append({
                        'name': band_name,
                        'url': band_url,
                        'element': band_link
                    })
                    print(f"밴드 발견: {band_name} ({band_url})")
            except Exception as e:
                continue
        
        # URL 기준으로 내림차순 정렬 (높은 숫자가 먼저 오도록)
        band_elements.sort(key=lambda x: int(x['url'].split('/')[-1]), reverse=True)
        
        total = len(band_elements)
        if (total > 0):
            print(f"총 {total}개의 밴드를 찾았습니다.")
            print(f"첫 번째 밴드: {band_elements[0]['name']} ({band_elements[0]['url']})")
            print(f"마지막 밴드: {band_elements[-1]['name']} ({band_elements[-1]['url']})")
        else:
            print("밴드를 찾을 수 없습니다.")
            return 1
        
        # 각 밴드에 글 작성
        success_count = 0
        for band_info in band_elements:
            print(f"밴드로 이동: {band_info['name']} ({band_info['url']})")
            if post_to_band(driver, config, band_info):
                success_count += 1
            time.sleep(10)  # 각 밴드 간 대기 시간
        
        print(f"모든 밴드 작성 완료 (성공: {success_count}, 실패: {total - success_count})")
        return 0
        
    except Exception as e:
        print(f"포스팅 실패: {str(e)}")
        return 1

def main():
    try:
        print("1. 설정 및 인증 데이터 로드")
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        # 밴드 URL 목록 로드
        if os.path.exists('band_urls.json'):
            with open('band_urls.json', 'r', encoding='utf-8') as f:
                config['bands'] = json.load(f)
                print(f"밴드 URL 로드 완료: {len(config['bands'])}개")

        print(f"이메일: {config['email'][:3]}***")
        print(f"URL: {config['post_url']}")
        print(f"제목: {config['title']}")
        
        print("\n2. Chrome 드라이버 설정 중...")
        
        # Chrome 프로필 경로 설정 (밴드 폴더 사용)
        profile_path = os.path.abspath(os.path.join('밴드', 'chrome_profile'))
        print(f"Chrome 프로필 경로: {profile_path}")
        
        if not os.path.exists(profile_path):
            print("⚠️ chrome_profile 폴더가 없습니다.")
            print("band_auto_poster.py를 실행하여 로그인 세션을 생성해주세요.")
            return 1
            
        # 프록시 연결 테스트
        try:
            print("프록시 연결 테스트 중...")
            response = requests.get('http://ipinfo.io', 
                                 proxies={'http': 'socks5h://127.0.0.1:1080',
                                         'https': 'socks5h://127.0.0.1:1080'},
                                 timeout=10)
            if response.status_code == 200:
                print(f"프록시 연결 성공: {response.json().get('country', 'Unknown')}")
            else:
                raise Exception("프록시 서버 응답 실패")
        except Exception as e:
            print(f"프록시 연결 실패: {str(e)}")
            return 1

        # Chrome 옵션 설정
        options = Options()
        options.add_argument(f'--user-data-dir={profile_path}')
        options.add_argument('--profile-directory=Default')
        options.add_argument('--proxy-server=socks5://127.0.0.1:1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        options.add_argument('--remote-debugging-port=9222')
        options.add_argument('--ignore-certificate-errors')  # SSL 인증서 검증 비활성화

        # Chrome 시작 전 대기
        time.sleep(5)  # 프록시 연결 안정화를 위한 대기
        
        driver = webdriver.Chrome(options=options)
        print("Chrome 드라이버 시작됨 (기존 프로필 사용)")
        
        try:
            return normal_posting_process(driver, config)
            
        finally:
            print("\n브라우저 종료")
            driver.quit()
            
    except Exception as e:
        print(f"\n치명적 오류: {str(e)}")
        return 1

if __name__ == "__main__":
    print("===== 밴드 자동 포스팅 시작 =====")
    sys.exit(main())