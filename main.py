import asyncio  
from playwright.async_api import async_playwright  
from datetime import datetime  
import os  
import shutil  
import zipfile  
import gspread  
import pandas as pd  
from oauth2client.service_account import ServiceAccountCredentials  
  
DOWNLOAD_DIR = "/tmp"  
  
# ==============================  
# Funções de renomear arquivos  
# ==============================  
def rename_downloaded_file(download_dir, download_path):  
    try:  
        print("🔹 [STEP 1] 📥 Iniciando renomeação do arquivo baixado...")  
        current_hour = datetime.now().strftime("%H")  
        new_file_name = f"PROD-{current_hour}.csv"  
        new_file_path = os.path.join(download_dir, new_file_name)  
        if os.path.exists(new_file_path):  
            print(f"🔹 [STEP 1] 🗑️ Removendo arquivo antigo: {new_file_path}")  
            os.remove(new_file_path)  
        shutil.move(download_path, new_file_path)  
        print(f"🔹 [STEP 1] ✅ Arquivo salvo como: {new_file_path}")  
        return new_file_path  
    except Exception as e:  
        print(f"🔹 [STEP 1] ❌ Erro ao renomear o arquivo: {e}")  
        return None  
  
  
# ==============================  
# Funções de atualização Google Sheets  
# ==============================  
def update_packing_google_sheets(csv_file_path):  
    try:  
        print("🔹 [STEP 2] 📥 Lendo o arquivo CSV...")  
        if not os.path.exists(csv_file_path):  
            print(f"🔹 [STEP 2] ❌ Arquivo {csv_file_path} não encontrado.")  
            return  
  
        print("🔹 [STEP 2] 🔐 Autenticando com Google Sheets...")  
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]  
        creds = ServiceAccountCredentials.from_json_keyfile_name("hxh.json", scope)  
        client = gspread.authorize(creds)  
  
        print("🔹 [STEP 2] 📊 Abrindo planilha no Google Sheets...")  
        sheet_url = "https://docs.google.com/spreadsheets/d/1LZ8WUrgN36Hk39f7qDrsRwvvIy1tRXLVbl3-wSQn-Pc/edit?gid=734921183#gid=734921183"  
        sheet1 = client.open_by_url(sheet_url)  
        worksheet1 = sheet1.worksheet("Base Ended")  
  
        print("🔹 [STEP 2] 📥 Lendo CSV com codificação robusta...")  
        df = pd.read_csv(  
            csv_file_path,  
            encoding='latin1',  
            engine='python',  
            on_bad_lines='skip',  
            skipinitialspace=True,  
            na_filter=False  
        ).fillna("")  
  
        if df.empty:  
            print("🔹 [STEP 2] ⚠️ O CSV está vazio após o processamento. Verifique o arquivo.")  
            return  
  
        print(f"🔹 [STEP 2] ✅ {len(df)} linhas e {len(df.columns)} colunas carregadas com sucesso.")  
  
        print("🔹 [STEP 2] 🗑️ Limpando a aba 'Base Ended'...")  
        worksheet1.clear()  
  
        print("🔹 [STEP 2] 📤 Enviando dados para o Google Sheets...")  
        worksheet1.update([df.columns.values.tolist()] + df.values.tolist())  
        print("🔹 [STEP 2] ✅ Dados enviados com sucesso para a aba 'Base Ended'.")  
  
    except Exception as e:  
        print(f"🔹 [STEP 2] ❌ Erro durante o processo: {e}")  
  
  
# ==============================  
# Fluxo principal Playwright  
# ==============================  
async def main():          
    print("🚀 [START] Iniciando o script de atualização do SPX")  
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)  
  
    async with async_playwright() as p:  
        print("🖥️  [STEP 0] 🖥️ Iniciando navegador Chromium...")  
        browser = await p.chromium.launch(  
            headless=False,   
            args=["--no-sandbox", "--disable-dev-shm-usage", "--window-size=1920,1080"]  
        )  
        context = await browser.new_context(accept_downloads=True)  
        page = await context.new_page()  
  
        try:  
            print("🌐 [STEP 1] 🌐 Navegando para o login do SPX...")  
            await page.goto("https://spx.shopee.com.br/")  
            await page.wait_for_selector('xpath=//*[@placeholder="Ops ID"]', timeout=15000)  
            print("✅ [STEP 1] Página de login carregada.")  
  
            print("🔐 [STEP 2] 🔐 Fazendo login...")  
            await page.locator('xpath=//*[@placeholder="Ops ID"]').fill('Ops115950')  
            await page.locator('xpath=//*[@placeholder="Senha"]').fill('@Shopee123')  
            await page.locator(  
                'xpath=/html/body/div[1]/div/div[2]/div/div/div[1]/div[3]/form/div/div/button'  
            ).click()  
            await page.wait_for_timeout(15000)  
            print("✅ [STEP 2] Login realizado com sucesso.")  
  
            try:  
                await page.locator('.ssc-dialog-close').click(timeout=5000)  
                print("✅ [STEP 2] Pop-up fechado.")  
            except:  
                print("🚫 [STEP 2] Nenhum pop-up foi encontrado. Pressionando Esc.")  
                await page.keyboard.press("Escape")  
  
            print("📂 [STEP 3] 📂 Navegando para 'Hub Linehaul Trips'...")  
            await page.goto("https://spx.shopee.com.br/#/hubLinehaulTrips/trip")  
            await page.wait_for_timeout(8000)  
  
            print("📊 [STEP 3] 📊 Clicando no botão 'Exportar'...")  
            await page.locator(  
                'xpath=/html[1]/body[1]/div[1]/div[1]/div[2]/div[2]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[4]/span[1]'  
            ).click()  
            await page.get_by_role("button", name="Exportar").nth(0).click()  
            await page.wait_for_timeout(240000)  
            print("⏳ [STEP 3] Exportação iniciada. Aguardando 4 minutos...")  
  
            print("📥 [STEP 4] 📥 Navegando para a aba de exportação de tarefas...")  
            await page.goto("https://spx.shopee.com.br/#/taskCenter/exportTaskCenter")  
            await page.wait_for_timeout(8000)  
  
            print("📥 [STEP 4] 📥 Iniciando download do arquivo...")  
            async with page.expect_download() as download_info:  
                await page.get_by_role("button", name="Baixar").nth(0).click()  
            download = await download_info.value  
            download_path = os.path.join(DOWNLOAD_DIR, download.suggested_filename)  
  
            print(f"📦 [STEP 4] 📥 Arquivo sugerido: {download.suggested_filename}")  
            print(f"💾 [STEP 4] 📥 Salvando arquivo: {download_path}")  
  
            # ✅ SALVA O ARQUIVO ANTES DE TENTAR EXTRAIR  
            await download.save_as(download_path)  
  
            # ✅ VERIFICA SE O ARQUIVO FOI SALVO  
            if not os.path.exists(download_path):  
                print(f"❌ [STEP 4] ❌ Arquivo não foi salvo: {download_path}")  
                return  
  
            print(f"✅ [STEP 4] ✅ Arquivo salvo com sucesso: {download_path}")  
  
            # ✅ VERIFICAÇÃO: se é ZIP, extrai o CSV dentro  
            if download.suggested_filename.lower().endswith('.zip'):  
                print("📦 [STEP 5] 📦 Arquivo é ZIP. Iniciando extração...")  
  
                try:  
                    # ✅ Verifica se o arquivo ZIP existe  
                    if not os.path.exists(download_path):  
                        print(f"❌ [STEP 5] ❌ Arquivo ZIP não encontrado: {download_path}")  
                        return  
  
                    with zipfile.ZipFile(download_path, 'r') as zip_ref:  
                        # Procura um arquivo CSV dentro do ZIP  
                        csv_files = [f for f in zip_ref.namelist() if f.lower().endswith('.csv')]  
                        if not csv_files:  
                            print("❌ [STEP 5] ❌ Nenhum arquivo CSV encontrado dentro do ZIP.")  
                            return  
                        # Usa o primeiro CSV encontrado  
                        csv_filename = csv_files[0]  
                        print(f"✅ [STEP 5] ✅ Encontrado CSV no ZIP: {csv_filename}")  
  
                        # Extrai o CSV para /tmp  
                        extracted_path = os.path.join(DOWNLOAD_DIR, csv_filename)  
                        with zip_ref.open(csv_filename) as csv_file:  
                            with open(extracted_path, 'wb') as f:  
                                f.write(csv_file.read())  
                        print(f"✅ [STEP 5] ✅ CSV extraído para: {extracted_path}")  
  
                        # Renomeia o CSV extraído  
                        new_file_path = rename_downloaded_file(DOWNLOAD_DIR, extracted_path)  
                        if not new_file_path:  
                            print("❌ [STEP 5] ❌ Falha ao renomear o CSV extraído.")  
                            return  
  
                        # Atualiza Google Sheets  
                        print("🔄 [STEP 6] 🔄 Atualizando Google Sheets...")  
                        update_packing_google_sheets(new_file_path)  
  
                        print("✅ [STEP 6] ✅ Dados atualizados com sucesso.")  
  
                except Exception as e:  
                    print(f"❌ [STEP 5] ❌ Erro ao extrair ZIP: {e}")  
                    return  
            else:  
                # ✅ Se não for ZIP, trata como CSV normal  
                print("📄 [STEP 5] 📄 Arquivo não é ZIP. Tratando como CSV direto.")  
  
                # ✅ Verifica se é CSV (com conteúdo)  
                try:  
                    content = await download.bytes()  
                    text_content = content.decode('latin1', errors='ignore')  
  
                    if any(',' in line for line in text_content.split('\n')[:5]):  
                        print("✅ [STEP 5] ✅ Arquivo parece ser CSV válido.")  
                    else:  
                        print("⚠️ [STEP 5] ⚠️ Arquivo NÃO parece ser CSV. Pode ser PDF ou erro.")  
                        txt_path = f"/tmp/{download.suggested_filename}.txt"  
                        with open(txt_path, "wb") as f:  
                            f.write(content)  
                        print(f"📝 [STEP 5] 📝 Salvando conteúdo como: {txt_path}")  
                        return  
  
                    # Renomeia  
                    new_file_path = rename_downloaded_file(DOWNLOAD_DIR, download_path)  
                    if not new_file_path:  
                        print("❌ [STEP 5] ❌ Falha ao renomear o arquivo.")  
                        return  
  
                    # Atualiza Google Sheets  
                    print("🔄 [STEP 6] 🔄 Atualizando Google Sheets...")  
                    update_packing_google_sheets(new_file_path)  
  
                    print("✅ [STEP 6] ✅ Dados atualizados com sucesso.")  
  
                except Exception as e:  
                    print(f"❌ [STEP 5] ❌ Erro ao processar arquivo: {e}")  
                    return  
  
        except Exception as e:  
            print(f"❌ [ERROR] ❌ Erro durante o processo: {e}")  
        finally:  
            print("🚪 [END] 🚪 Fechando o navegador...")  
            await browser.close()  
            print("✅ [END] ✅ Script finalizado.")  
  
if __name__ == "__main__":  
    asyncio.run(main()) 
