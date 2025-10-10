import asyncio  
from playwright.async_api import async_playwright  
from datetime import datetime  
import os  
import shutil  
import gspread  
import pandas as pd  
from oauth2client.service_account import ServiceAccountCredentials  
  
DOWNLOAD_DIR = "/tmp"  
  
# ==============================  
# Funções de renomear arquivos  
# ==============================  
def rename_downloaded_file(download_dir, download_path):  
    try:  
        print("[INFO] 📥 Iniciando renomeação do arquivo baixado...")  
        current_hour = datetime.now().strftime("%H")  
        new_file_name = f"PROD-{current_hour}.csv"  
        new_file_path = os.path.join(download_dir, new_file_name)  
        if os.path.exists(new_file_path):  
            print(f"[INFO] 🗑️ Removendo arquivo antigo: {new_file_path}")  
            os.remove(new_file_path)  
        shutil.move(download_path, new_file_path)  
        print(f"[OK] ✅ Arquivo salvo como: {new_file_path}")  
        return new_file_path  
    except Exception as e:  
        print(f"[ERROR] ❌ Erro ao renomear o arquivo: {e}")  
        return None  
  
  
# ==============================  
# Funções de atualização Google Sheets  
# ==============================  
def update_packing_google_sheets(csv_file_path):  
    try:  
        print(f"[INFO] 📥 Lendo o arquivo CSV: {csv_file_path}")  
        if not os.path.exists(csv_file_path):  
            print(f"[ERROR] ❌ Arquivo {csv_file_path} não encontrado.")  
            return  
  
        print("[INFO] 🔐 Autenticando com Google Sheets...")  
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]  
        creds = ServiceAccountCredentials.from_json_keyfile_name("hxh.json", scope)  
        client = gspread.authorize(creds)  
  
        print("[INFO] 📊 Abrindo planilha no Google Sheets...")  
        sheet_url = "https://docs.google.com/spreadsheets/d/1LZ8WUrgN36Hk39f7qDrsRwvvIy1tRXLVbl3-wSQn-Pc/edit?gid=734921183#gid=734921183"  
        sheet1 = client.open_by_url(sheet_url)  
        worksheet1 = sheet1.worksheet("Base Ended")  
  
        print("[INFO] 📥 Lendo CSV com codificação robusta...")  
        df = pd.read_csv(  
            csv_file_path,  
            encoding='latin1',  
            engine='python',  
            on_bad_lines='skip',  
            skipinitialspace=True,  
            na_filter=False  
        ).fillna("")  
  
        if df.empty:  
            print("[WARNING] ⚠️ O CSV está vazio após o processamento. Verifique o arquivo.")  
            return  
  
        print(f"[INFO] ✅ {len(df)} linhas e {len(df.columns)} colunas carregadas com sucesso.")  
  
        print("[INFO] 🗑️ Limpando a aba 'Base Ended'...")  
        worksheet1.clear()  
  
        print("[INFO] 📤 Enviando dados para o Google Sheets...")  
        worksheet1.update([df.columns.values.tolist()] + df.values.tolist())  
        print(f"[OK] ✅ Dados enviados com sucesso para a aba 'Base Ended'.")  
  
    except Exception as e:  
        print(f"[ERROR] ❌ Erro durante o processo: {e}")  
  
  
# ==============================  
# Fluxo principal Playwright  
# ==============================  
async def main():          
    print("[INFO] 🚀 Iniciando o script de atualização do SPX")  
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)  
  
    async with async_playwright() as p:  
        print("[INFO] 🖥️ Iniciando navegador Chromium...")  
        browser = await p.chromium.launch(  
            headless=False,   
            args=["--no-sandbox", "--disable-dev-shm-usage", "--window-size=1920,1080"]  
        )  
        context = await browser.new_context(accept_downloads=True)  
        page = await context.new_page()  
  
        try:  
            print("[INFO] 🌐 Navegando para o login do SPX...")  
            await page.goto("https://spx.shopee.com.br/")  
            await page.wait_for_selector('xpath=//*[@placeholder="Ops ID"]', timeout=15000)  
            print("[INFO] ✅ Página de login carregada.")  
  
            print("[INFO] 🔐 Fazendo login...")  
            await page.locator('xpath=//*[@placeholder="Ops ID"]').fill('Ops115950')  
            await page.locator('xpath=//*[@placeholder="Senha"]').fill('@Shopee123')  
            await page.locator(  
                'xpath=/html/body/div[1]/div/div[2]/div/div/div[1]/div[3]/form/div/div/button'  
            ).click()  
            await page.wait_for_timeout(15000)  
            print("[INFO] ✅ Login realizado com sucesso.")  
  
            try:  
                await page.locator('.ssc-dialog-close').click(timeout=5000)  
                print("[INFO] ✅ Pop-up fechado.")  
            except:  
                print("[INFO] 🚫 Nenhum pop-up foi encontrado. Pressionando Esc.")  
                await page.keyboard.press("Escape")  
  
            # NAVEGAÇÃO E DOWNLOAD 1  
            print("[INFO] 📂 Navegando para 'Hub Linehaul Trips'...")  
            await page.goto("https://spx.shopee.com.br/#/hubLinehaulTrips/trip")  
            await page.wait_for_timeout(8000)  
  
            print("[INFO] 📊 Clicando no botão 'Exportar'...")  
            await page.locator(  
                'xpath=/html[1]/body[1]/div[1]/div[1]/div[2]/div[2]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[4]/span[1]'  
            ).click()  
            await page.get_by_role("button", name="Exportar").nth(0).click()  
            await page.wait_for_timeout(240000)  
            print("[INFO] 📥 Exportação iniciada. Aguardando 4 minutos...")  
  
            # 👉 Botão de download 1  
            print("[INFO] 📥 Navegando para a aba de exportação de tarefas...")  
            await page.goto("https://spx.shopee.com.br/#/taskCenter/exportTaskCenter")  
            await page.wait_for_timeout(8000)  
  
            print("[INFO] 📥 Iniciando download do arquivo...")  
            async with page.expect_download() as download_info:  
                await page.get_by_role("button", name="Baixar").nth(0).click()  
            download = await download_info.value  
            download_path = os.path.join(DOWNLOAD_DIR, download.suggested_filename)  
            await download.save_as(download_path)  
            print(f"[INFO] ✅ Arquivo baixado: {download_path}")  
  
            # Renomear  
            new_file_path = rename_downloaded_file(DOWNLOAD_DIR, download_path)  
            if not new_file_path:  
                print("[ERROR] ❌ Falha ao renomear o arquivo.")  
                return  
  
            # Atualizar Google Sheets  
            print("[INFO] 🔄 Atualizando Google Sheets...")  
            update_packing_google_sheets(new_file_path)  
  
            print("[OK] ✅ Dados atualizados com sucesso.")  
  
        except Exception as e:  
            print(f"[ERROR] ❌ Erro durante o processo: {e}")  
        finally:  
            print("[INFO] 🚪 Fechando o navegador...")  
            await browser.close()  
            print("[OK] ✅ Script finalizado.")  
  
if __name__ == "__main__":  
    asyncio.run(main())
