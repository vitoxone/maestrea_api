from fastapi import FastAPI, Query, HTTPException, Depends
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, TimeoutException
import requests
from send_mail import send_email
from datetime import datetime, timedelta
import sys
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session  # asegúrate de tener este import correcto
from sqlalchemy.orm import selectinload,joinedload
from sqlalchemy import func, select, asc, desc, text
from schemas.Product import ProductWithStore, ProductsPage, ProductRead
from uuid import UUID




import logging
import time
import traceback

app = FastAPI()

import threading
stop_event = threading.Event()

import signal

def handle_sigint(signum, frame):
    print("🛑 Señal de interrupción recibida (Ctrl+C)")
    stop_event.set()

signal.signal(signal.SIGINT, handle_sigint)

# ------------------------- Configuración Mongo -------------------------
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "maestrea"
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]
products_collection = db.products
pages_collection = db.pages
prices_collection = db.prices
categories_collection = db.prices
subcategories_collection = db.prices

# ------------------------- Selenium Helper -------------------------
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

# ------------------------- Utilidades -------------------------
def current_date():
    return datetime.utcnow()

def scrape_product_details(url):
    driver = get_driver()
    driver.get(url)
    time.sleep(2)

    data = {}

    try:
        data["brand"] = driver.find_element(By.CSS_SELECTOR, ".marca").text.strip()
    except:
        data["brand"] = None

    try:
        data["name"] = driver.find_element(By.CSS_SELECTOR, ".nombre").text.strip()
    except:
        data["name"] = None

    try:
        data["sku"] = driver.find_element(By.CSS_SELECTOR, ".sku").text.strip().replace("SKU: ", "")
    except:
        data["sku"] = None

    try:
        price_element = driver.find_element(By.CSS_SELECTOR, ".precio")
        driver.execute_script("var s = arguments[0].querySelector('small'); if(s) s.remove();", price_element)
        price_text = price_element.text.strip()
        data["price"] = int(''.join(filter(str.isdigit, price_text)))
    except:
        data["price"] = None

    try:
        data["stock"] = driver.find_element(By.CSS_SELECTOR, ".stock").text.replace("Stock: ", "").strip()
    except:
        data["stock"] = None

    try:
        main_img = driver.find_element(By.CSS_SELECTOR, ".imagen a img").get_attribute("src")
        data["main_image"] = main_img
    except:
        data["main_image"] = None

    try:
        thumbs = driver.find_elements(By.CSS_SELECTOR, ".thumbsGaleriaFicha a")
        data["gallery"] = [thumb.get_attribute("href") for thumb in thumbs]
    except:
        data["gallery"] = []

    driver.quit()
    return data

def handle_pagination(driver, paginator_config):
    try:
        if paginator_config:
            # ✅ PAGINACIÓN POR BOTÓN "SIGUIENTE"
            if paginator_config["type"] == "next_button":
                try:
                    # current_page = driver.find_element(By.CSS_SELECTOR, paginator["current_page"])
                    # driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", current_page)
                    # time.sleep(1)
                    next_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, paginator_config["next_page"]))
                    )
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                    # Verificar si el botón está oculto (d-none) o deshabilitado (disabled)

                    if "d-none" in next_button.get_attribute("class"):
                        print("✅ Botón 'Siguiente' deshabilitado. Fin de la paginación.")
                        return False  # Indicar que no hay más páginas
                    
                        # 1️⃣ Verificar si tiene el atributo 'disabled'
                    if next_button.get_attribute("disabled"):
                        print("✅ Botón 'Siguiente' está deshabilitado (por atributo).")
                        return False

                    # 2️⃣ Verificar si el botón tiene la clase 'disabled'
                    if "disabled" in next_button.get_attribute("class"):
                        print("✅ Botón 'Siguiente' está deshabilitado (por clase).")
                        return False

                    # 3️⃣ Verificar si el botón está visible e interactuable
                    if not next_button.is_displayed() or not next_button.is_enabled():
                        print("✅ Botón 'Siguiente' no es interactuable.")
                        return False

                    print("➡️ Haciendo clic en el botón 'Siguiente'...")
                    driver.execute_script("arguments[0].click();", next_button)  # Forzar clic en headless
                   # WebDriverWait(driver, 10).until(EC.staleness_of(next_button))  # Esperar cambio de DOM

                    return True  # Indica que hay más páginas
                except TimeoutException:
                    print("❌ TimeoutException: Botón 'Siguiente' no encontrado. Fin de la paginación.")
                    return False  # Indicar que la paginación ha terminado
    
                except NoSuchElementException:
                    print("❌ NoSuchElementException: Botón 'Siguiente' no encontrado. Fin de la paginación.")
                    return False
                except ElementClickInterceptedException:
                    print("⚠️ ElementClickInterceptedException: No se pudo hacer clic en 'Siguiente'. Intentando con JavaScript...")
                    driver.execute_script("arguments[0].click();", next_button)

            # ✅ PAGINACIÓN POR NÚMEROS DE PÁGINA
            elif paginator_config["type"] == "page_numbers":
                try:
                    # Encontrar la página activa
                    current_page = driver.find_element(By.CSS_SELECTOR, paginator_config["current_page"])
                    print(f"📍 Página actual: {current_page.text.strip()}")

                    # Buscar la siguiente página (hermano siguiente en el DOM)
                    next_page = current_page.find_element(By.XPATH, paginator_config["next_page"])
                    print(f"📍 Página siguiente: {current_page.text.strip()}")


                    # Hacer scroll y esperar que la página sea clickeable
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_page)
                    WebDriverWait(driver, 5).until(EC.element_to_be_clickable(next_page))

                    print(f"➡️ Cambiando a página: {next_page.text.strip()}")
                    driver.execute_script("arguments[0].click();", next_page)  # Forzar clic en headless
                    #WebDriverWait(driver, 10).until(EC.staleness_of(current_page))  # Esperar cambio de DOM

                except NoSuchElementException:
                    print("✅ No hay más páginas disponibles.")
                    return False
                except ElementClickInterceptedException:
                    print("⚠️ No se pudo hacer clic en la siguiente página. Intentando con JavaScript...")
                    driver.execute_script("arguments[0].click();", next_page)       

            return True  # Indica que hay más páginas

        else:
            print("❌ No se encontró configuración de paginación en 'config'.")
            return False

    except Exception as e:
        # print(f"❌ Error en paginación: {e}")
        logging.error(f"Error en paginación: {e}")
        traceback.print_exc() 
        return False
    

# ------------------------- Scraper 1: obtener vista previa -------------------------
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from models.Store import Store
from models.Product import Product
from models.Price import Price
from models.Link import Link
from models.Subcategory import Subcategory
from models.Category import Category

from app.database import get_db
import uuid


async def get_store_by_id(store_id: uuid.UUID, db: AsyncSession) -> Store:
    result = await db.execute(select(Store).where(Store.id == store_id))
    return result.scalar_one_or_none()
async def get_links_for_store(store_id: uuid.UUID, db: AsyncSession):
    try:
        result = await db.execute(
            select(Link.id, Link.url).where(
                (Link.id_store == store_id) &
                (Link.active == True) &
                (Link.deleted == False)
            )
        )
        return [{"id": row[0], "url": row[1]} for row in result.all()]

    except Exception as e:
        print(f"❌ Error al obtener los links: {e}")
        return []

from sqlalchemy.ext.asyncio import AsyncSession
 # asegúrate de importar correctamente tu `async_session`

# from tenacity import retry, stop_after_attempt, wait_fixed

from sqlalchemy import select
from sqlalchemy.pool import Pool
import logging, asyncio

logging.basicConfig(level=logging.INFO)

async def debug_session(urls_scrapeadas):
    async with async_session() as session:

        # --- Estado del pool ---
        bind = session.get_bind()          # AsyncEngine
        logging.info(bind.pool.status())   # "Pool size: 20  Connections in pool: 1 Current overflow: 0 ..."

        # --- Estado de la sesión ---
        logging.info("in_transaction: %s", session.in_transaction())
        logging.info("is_active:      %s", session.is_active)
        logging.info("new/dirty:      %s / %s", session.new, session.dirty)

        # --- Estado de la conexión asociada ---
        conn = await session.connection()  # AsyncConnection
        logging.info("conn.closed:     %s", conn.closed)
        logging.info("conn.invalidated:%s", conn.invalidated)

        # Ahora sí, tu consulta
        result = await session.execute(
            select(Product.url).where(Product.url.in_(urls_scrapeadas))
        )
        existentes = set(result.scalars())
        return existentes
    
# # @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
# async def guardar_productos_nuevos(nuevos: list[dict], session: ):

#     if nuevos:
#         session.add_all(nuevos)
#         await session.commit()
#         print(f"✅ {len(nuevos)} productos nuevos guardados")
#     else:
#         print("📭 No hay productos nuevos para guardar.")

async def guardar_producto(producto):
    async with get_db() as session:
        session.add(producto)
        await session.commit()


async def scrape_overview_products(store_id: uuid.UUID):
        async with async_session() as session:
            store = await get_store_by_id(store_id, session)
            if not store:
                print("Store no encontrada")
                return
            urls  = await get_links_for_store(store.id, session)

        selectors = store.selectors
        product_card_selector = selectors['box']["product_card"]
        title_selector = selectors['box']["title"]
        link_selector = selectors['box']["link"]
        paginator_config = store.paginator

        def scrape():
            driver = get_driver()
            products = []

            for url in urls:
                print(url)
                driver.get(url['url'])
                page_number = 1
                while True:
                    print(f"📄 Scraping enlaces de la página {page_number}...")
                    time.sleep(3)
                    try:
                        cards = driver.find_elements(By.CSS_SELECTOR, product_card_selector)
                    except Exception as e:
                        print(f"Error obteniendo listado de productos: {e}")
                        break

                    for card in cards:
                        try:
                            try:
                                stock_element = card.find_element(By.CSS_SELECTOR, ".stock.unavailable")
                                if "No disponible" in stock_element.text:
                                    break
                            except:
                                pass
                            title = card.find_element(By.CSS_SELECTOR, title_selector).text
                            if link_selector == 'this':
                                 link = card.get_attribute("href")   
                            else :
                                link = card.find_element(By.CSS_SELECTOR, link_selector).get_attribute("href")
                            products.append({
                                "name": title,
                                "url": link,
                                "link_id": url['id'],
                            })
                            print(title)
                        except Exception as e:
                            print(f"Error procesando producto: {e}")

                    if paginator_config:
                        paginate = handle_pagination(driver, paginator_config)
                        if paginate:
                            page_number += 1
                        else:
                            break

            driver.quit()
            return products

        results = await asyncio.to_thread(scrape)

        # async with async_session() as session:
        #     # 👉 Acumulamos los productos nuevos
        #     nuevos_productos = []
        #     for prod in results:
        #         result = await session.execute(select(Product).where(Product.url == prod["url"]))
        #         if not result.scalar():
        #             nuevos_productos.append(Product(
        #                 id=uuid.uuid4(),
        #                 name=prod["name"],
        #                 url=prod["url"],
        #                 link_id=prod["link_id"],
        #                 status="incompleto",
        #                 created=current_date(),
        #                 category_id=uuid.UUID("4c947d6d-d043-44da-a028-81cb6c4b0011"),
        #                 subcategory_id=uuid.UUID("1f532211-2e1a-4fc9-9c72-ad47b4ba54a2")
        #         ))

        #     # ✅ Guardamos todos juntos
        #     if nuevos_productos:
        #         session.add_all(nuevos_productos)
        #         await session.commit()
        #         print(f"✅ {len(nuevos_productos)} productos nuevos guardados")
        #     else:
        #         print("📭 No hay productos nuevos para guardar.")
        from itertools import islice
        from sqlalchemy import bindparam, select

        BATCH = 300

        # 0️⃣  DEDUPLICA el resultado crudo del scraper
        visto = set()                  # URLs ya vistas en este lote
        results_unicos = []
        for p in results:
            url = p["url"]
            if url and url not in visto:
                visto.add(url)         # marca la URL como procesada
                results_unicos.append(p)

        urls_scrapeadas = [p["url"] for p in results_unicos]
        ids_links_store = list({item["id"] for item in urls})        # también sin duplicados

        # 1️⃣  Trae de una vez las URLs que YA existen en la base
        async with async_session() as session:
            stmt = (
                select(Product.url)
                .where(
                    (Product.url.in_(bindparam("urls", expanding=True))) &
                    (Product.link_id.in_(ids_links_store))
                )
            )
            res = await session.execute(stmt, {"urls": urls_scrapeadas})
            existentes = set(res.scalars())

        # 2️⃣  Construye solo los que faltan (y ya son únicos en este lote)
        nuevos_productos = [
            Product(
                id=uuid.uuid4(),
                name=p["name"],
                url=p["url"],
                link_id=p["link_id"],
                status="incompleto",
                created=current_date(),
                category_id=uuid.UUID("4c947d6d-d043-44da-a028-81cb6c4b0011"),
                subcategory_id=uuid.UUID("1f532211-2e1a-4fc9-9c72-ad47b4ba54a2"),
            )
            for p in results_unicos
            if p["url"] not in existentes
        ]

        # 3️⃣  Inserta por lotes
        def batched(iterable, size):
            it = iter(iterable)
            while (batch := list(islice(it, size))):
                yield batch

        async with async_session() as session:
            for chunk in batched(nuevos_productos, BATCH):
                session.add_all(chunk)
                await session.flush()
            await session.commit()

def extract_category_info(breadcrumb_items):
    try:
        if len(breadcrumb_items) >= 2:
            category = breadcrumb_items[-2].text.strip()
            subcategory = breadcrumb_items[-1].text.strip()
        elif len(breadcrumb_items) == 1:
            category = breadcrumb_items[0].text.strip()
            subcategory = None
        else:
            category = subcategory = None
        return category, subcategory
    except Exception as e:
        print(f"❌ Error al extraer categoría: {e}")
        return None, None
    
def chunkify(lst, n):
    return [lst[i::n] for i in range(n)]   
# ------------------------- Scraper 2: completar detalles -------------------------
async def check_url_exists(url: str, max_retries: int = 3, delay: float = 1.0) -> bool:
    for attempt in range(1, max_retries + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.head(url, allow_redirects=True, timeout=5) as resp:
                    if resp.status < 400:
                        return True
                    else:
                        print(f"⚠️ Intento {attempt}: status {resp.status} para {url}")
        except Exception as e:
            print(f"❌ Intento {attempt}: Verificación URL fallida: {e}")
        
        if attempt < max_retries:
            await asyncio.sleep(delay)  # espera entre intentos

    return False  # todos los intentos fallaron

async def complete_product_details(parallel_chunks=1, max_total=5000, db: AsyncSession = Depends(get_db)):
    # 1. Obtener productos incompletos una sola vez
    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.status == "incompleto").limit(max_total))
        products = result.scalars().all()

    chunks = chunkify(products, parallel_chunks)

    async def process_batch(batch, thread_id):
        driver = get_driver()  # ✅ Solo un WebDriver por batch
        try:
            async with async_session() as session:
                for product in batch:
                    if stop_event.is_set():
                        print(f"🛑 [{thread_id}] Cancelado antes de procesar producto")
                        return

                    try:
                        # Reconsulta el producto en esta sesión
                        product_id = product.id
                        product = await session.get(Product, product_id, options=[selectinload(Product.link).selectinload(Link.store)])
                        selectors = product.link.store.selectors or {}

                        # Verifica URL primero con aiohttp
                        if not await check_url_exists(product.url):
                            print(f"❌ [{thread_id}] URL inválida: {product.url}")
                            product.deleted = True
                            product.status = "deleted"
                            session.add(product)
                            await session.commit()
                            continue

                        driver.get(product.url)

                        def safe(selector_key):
                            try:
                                return driver.find_element(By.CSS_SELECTOR, selectors['detail'][selector_key]).text.strip()
                            except:
                                return None

                        def safe_attr(selector_key, attr):
                            try:
                                return driver.find_element(By.CSS_SELECTOR, selectors['detail'][selector_key]).get_attribute(attr)
                            except:
                                return None

                        def safe_list(selector_key):
                            try:
                                return [t.get_attribute("href") for t in driver.find_elements(By.CSS_SELECTOR, selectors['detail'][selector_key])]
                            except:
                                return []

                        try:
                            price_element = driver.find_element(By.CSS_SELECTOR, selectors['detail']['price'])
                            driver.execute_script("""
                                let span = arguments[0].querySelector('span');
                                if (span) span.remove();
                                let small = arguments[0].querySelector('small');
                                if (small) small.remove();
                            """, price_element)
                            price_text = price_element.text.strip()
                            price = int(''.join(filter(str.isdigit, price_text)))
                        except:
                            product.status = "deleted"
                            product.deleted = True
                            session.add(product)
                            await session.commit()
                            continue

                        try:
                            breadcrumb_items = driver.find_elements(By.CSS_SELECTOR, selectors['detail']['breadcrumb_items'])
                            category, subcategory = extract_category_info(breadcrumb_items)
                        except:
                            category = subcategory = None

                        # Buscar o crear categoría
                        category_obj = None
                        if category:
                            result = await session.execute(select(Category).where(Category.name == category))
                            category_obj = result.scalars().first()
                            if not category_obj:
                                category_obj = Category(
                                    id=uuid.uuid4(),
                                    name=category,
                                    active=True,
                                    deleted=False,
                                    created=current_date()
                                )
                                session.add(category_obj)
                                await session.flush()
                                await session.refresh(category_obj)

                        # Buscar o crear subcategoría
                        subcategory_obj = None
                        if subcategory and category_obj:
                            result = await session.execute(
                                select(Subcategory).where(
                                    Subcategory.name == subcategory,
                                    Subcategory.category_id == category_obj.id
                                )
                            )
                            subcategory_obj = result.scalars().first()
                            if not subcategory_obj:
                                subcategory_obj = Subcategory(
                                    id=uuid.uuid4(),
                                    name=subcategory,
                                    category_id=category_obj.id,
                                    active=True,
                                    deleted=False,
                                    created=current_date()
                                )
                                session.add(subcategory_obj)
                                await session.flush()
                                await session.refresh(subcategory_obj)

                        # Actualiza el producto
                        product.name = safe("name")
                        product.brand = safe("brand")
                        product.sku = safe("sku")
                        product.price = price
                        product.stock = safe("stock")
                        product.main_image = safe_attr("main_image", "src")
                        product.gallery = safe_list("gallery")
                        product.category_id = category_obj.id if category_obj else None
                        product.subcategory_id = subcategory_obj.id if subcategory_obj else None
                        product.status = "publicado"
                        product.modified = current_date()

                        session.add(product)
                        await session.commit()
                        print(f"✅ [{thread_id}] Procesado: {product.name or product.url}")

                    except Exception as e:
                        await session.rollback()
                        print(f"❌ [{thread_id}] Error procesando producto {getattr(product, 'url', '')}: {e}")
        finally:
            driver.quit()  # ✅ se cierra solo una vez

    stop_event.clear()
    tasks = [process_batch(chunk, i + 1) for i, chunk in enumerate(chunks)]
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("🛑 Cancelado por el usuario con Ctrl+C")
        for task in tasks:
            task.cancel()
        raise
# ------------------------- Scraper 3: detectar cambios de precio -------------------------
async def detect_price_changes(parallel_chunks=4, max_total=5000):
    # Definir "hoy" en UTC (sin horas)
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    
    cursor = products_collection.find({"status": "publicado", "deleted" : False}).limit(max_total)
    products = await cursor.to_list(length=max_total)
    print(products)
    chunks = chunkify(products, parallel_chunks)

    async def process_batch(batch, thread_id):
        for index, product in enumerate(batch, start=1):
            page = await pages_collection.find_one({"_id": product["page_id"]})
            selectors = page.get("selectors", {})

            def check_price():
                try:
                    response = requests.head(product["url"], allow_redirects=True, timeout=5)
                    if response.status_code >= 400:
                        print(f"❌ [{thread_id}] URL inválida: {product['url']}")
                        return "deleted"
                except Exception as e:
                    print(f"❌ [{thread_id}] Verificación URL fallida: {e}")
                    return "deleted"
                
                driver = get_driver()
                driver.get(product["url"])
                time.sleep(3)
                try:
                    print(product["name"])
                    price_element = driver.find_element(By.CSS_SELECTOR, selectors['detail']['price'])
                    driver.execute_script("""
                        let span = arguments[0].querySelector('span');
                        if (span) span.remove();
                        let small = arguments[0].querySelector('small');
                        if (small) small.remove();
                    """, price_element)
                    price_text = price_element.text.strip()
                    new_price = int(''.join(filter(str.isdigit, price_text)))
                except:
                    new_price = None
                driver.quit()
                return new_price

            new_price = await asyncio.to_thread(check_price)

            print(f"✅ [{thread_id}] Procesado: {product.get('name', product['url'])}")

            print(f"{product["details"]["price"]} / {new_price}")

            if new_price is None or new_price == 'deleted':
                await products_collection.update_one(
                    {"_id": product["_id"]},
                    {"$set": {"status": "desactivado", "last_checked": current_date()}}
                )
            elif new_price != product["details"]["price"]:
                await products_collection.update_one(
                    {"_id": product["_id"]},
                    {"$set": {"details.price": new_price, "last_checked": current_date()}}
                )

                new_price_docuemnt = {
                    "product_id": product["_id"],  # renombramos _id para no duplicarlo
                    "price": product["details"]["price"],
                    "date":  current_date()
                }
                await prices_collection.insert_one(new_price_docuemnt)

                if new_price < 0.5 * product["details"]["price"]:
                    text = f"El producto {product["name"]} ha bajado de {product["details"]["price"]} a {new_price} \n ID: {product["_id"]}"

                    send_email(
                        to_email="vitox.one@gmail.com",
                        subject="Cambio de precio detectado",
                        text= text
                    )
                else:
                    print(f"cambio de precio menor a 50% en {product["name"]} ID: {product["_id"]}")  
            else:
                await products_collection.update_one(
                    {"_id": product["_id"]},
                    {"$set": {"last_checked": current_date()}}
                )      
    # Ejecutar todos los bloques en paralelo
    tasks = [process_batch(chunk, i+1) for i, chunk in enumerate(chunks)]
    await asyncio.gather(*tasks)  


def click_element(selector, driver, element):
    print('Hacer clic en un botón o enlace')  
    try:
        wait = WebDriverWait(driver, 10)
        button = driver.find_element(By.CSS_SELECTOR, selector)
        driver.execute_script("arguments[0].scrollIntoView(true);", button)
        time.sleep(1)  # opcional, para dar tiempo al scroll
        print(button.is_displayed(), button.is_enabled())
        driver.execute_script("arguments[0].click();", button)
        #button.click()
        # menu_trigger = wait.until(EC.element_to_be_clickable((By.XPATH, "//div[contains(@class, 'dNxqUP')]")))
        # print(menu_trigger)
        print(button)

        if(button):
            tag_name = button.tag_name
            print(tag_name)
            wait = WebDriverWait(driver, 10)
            if tag_name in ("button", "link"):
                button.click()
            elif tag_name in ("div", "i"):
                driver.execute_script("""
                    var button = arguments[0];
                    button.setAttribute("role", "button"); 
                    button.setAttribute("tabindex", "0");
                    button.click();
                """, button)
            else:
                button.click()    
        #visualización
        #os.getenv("VISUAL_DEBUG") == "True" and benefit.highlight_element_temp(driver, button)

        else:
            print("error en click")
    except:
        try:
            # Obtener el atributo `onclick`
            onclick_attribute = button.get_attribute("onclick")

            # if onclick_attribute:
            print(f"🔍 `onclick` encontrado: {onclick_attribute}")

            # Intentar hacer clic normalmente
            try:
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                WebDriverWait(driver, 3).until(EC.element_to_be_clickable(button)).click()
                wait = WebDriverWait(driver, 10)
                try:
                    # Esperar explícitamente a que el enlace esté visible, no solo presente
                    menu_item = wait.until(EC.visibility_of_element_located((By.LINK_TEXT, "PROYECTO E IDEAS")))
                    print("✅ Menú desplegado y enlace visible.")
                    menu_item.click()
                except Exception as e:
                    print("❌ El menú no se desplegó correctamente:", e)
                print("✅ Click realizado con éxito (normal).")
            except:
                print("⚠️ Click normal falló. Intentando con JavaScript...")
                driver.execute_script(onclick_attribute)  # Ejecutar el evento `onclick` con JavaScript
                print("✅ Click realizado con éxito (JavaScript).")

            # else:
            #     print("❌ No se encontró `onclick` en el beneficio.")

        except Exception as e:
            print(f"❌ Error al hacer clic en el beneficio: {e}")              


def extractLinks(url):
    import requests
    from bs4 import BeautifulSoup
    from urllib.parse import unquote
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from bs4 import BeautifulSoup
    import time
    import sys

    options = Options()
    options.headless = False
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)
        time.sleep(5)  # Ajusta el tiempo si la carga es lenta

        wait = WebDriverWait(driver, 10)

        # 1. Hacer clic en el trigger del menú
        menu_trigger = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.dNxqUP")))
        menu_trigger.click()

        # 2. Esperar a que el menú tenga visibilidad completa y esté listo
        try:
            # Esperar explícitamente a que el enlace esté visible, no solo presente
            menu_item = wait.until(EC.visibility_of_element_located((By.LINK_TEXT, "PROYECTO E IDEAS")))
            print("✅ Menú desplegado y enlace visible.")
            menu_item.click()
        except Exception as e:
            print("❌ El menú no se desplegó correctamente:", e)
        #click_element("div.osf__sc-d9hb4p-0", driver, boton_menu)

        # print(boton_menu)

        # boton_menu.click()

        # osf__sc-d9hb4p-0 osf__sc-16ucmf-2 jRBkAY iQqkbm

        # time.sleep(2)

        # soup = BeautifulSoup(driver.page_source, 'html.parser')
        # div = soup.select_one("div.osf__sc-u2c9wh-0 eREGKW")

        # if div:
        #     print("✅ Div encontrado. Contenido:")
        #     print(div.text.strip()[:500])  # Muestra primeros 500 caracteres
        # else:
        #     print("❌ Div no encontrado.")

    finally:
        driver.quit()
    

async def load_prices():
    cursor = products_collection.find(
        { "details.old_prices": { "$exists": True } },
        { "_id": 1, "page_id": 1, "details.old_prices": 1 }
    )

    async for doc in cursor:        
        new_doc = {
            "product_id": doc["_id"],  # renombramos _id para no duplicarlo
            "page_id": doc.get("page_id"),
            "price": doc["details"]["old_prices"][0]['price'],
            "date":  doc["details"]["old_prices"][0]['date']
        }
        await prices_collection.insert_one(new_doc)
        print(doc)
# ------------------------- Endpoints API -------------------------
@app.post("/scrape/{store_id}")
async def trigger_scrape_overview(
    store_id: uuid.UUID
):
    await scrape_overview_products(store_id)
    return {"status": "ok", "message": "Scraping completado"}

@app.post("/complete")
async def trigger_complete_details(db: AsyncSession = Depends(get_db)):

    # await load_prices()

    await complete_product_details(parallel_chunks=8, max_total=5000, db=db)
    return {"status": "ok", "message": "Detalles completados en paralelo"}

@app.post("/check-prices")
async def trigger_price_check():
    await detect_price_changes(parallel_chunks=4, max_total=5000)
    return {"status": "ok", "message": "Revisión de precios finalizada"}
def transform_objectid(obj):
    """Convierte todos los ObjectId en str, de forma recursiva."""
    if isinstance(obj, list):
        return [transform_objectid(item) for item in obj]
    elif isinstance(obj, dict):
        new_obj = {}
        for key, value in obj.items():
            if isinstance(value, ObjectId):
                new_obj[key] = str(value)
            else:
                new_obj[key] = transform_objectid(value)
        return new_obj
    else:
        return obj

@app.get("/products", response_model=ProductsPage)
async def get_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    sort: str | None = Query(None, pattern="^(price|name)_(asc|desc)$"),
    category: str | None = Query(None),
    status: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        # # 1️⃣  Construye el SELECT base
        # stmt = select(Product).where(Product.deleted.is_(False))
        #SELECT * FROM products WHERE products.deleted = False
        stmt = (
            select(
                Product,
                Store.webpage.label("webpage"),
                Store.name.label("store_name")
            )
            .join(Product.link)          # Join a Link
            .join(Link.store)            # Join a Store
            .options(                    
                joinedload(Product.link).joinedload(Link.store) # Join products.
            )
            .where(Product.deleted.is_(False))
        )
        #SELECT products.*, stores.webpage, stores.name as store_name FROM products 
        #JOIN links ON (products.id_link = links.id)
        #JOIN stores ON (links.id_store = stores.id)  
        #WHERE products.deleted = False

        # 2️⃣  Filtros dinámicos
        if search:
            stmt = stmt.where(Product.name.ilike(f"%{search}%"))   # ILIKE = case-insensitive
        if category:
            stmt = stmt.where(Product.category_id == category)
        if status:
            stmt = stmt.where(Product.status == status) 

        # 3️⃣  Total antes de paginar
        total_subq = select(func.count()).select_from(stmt.subquery())
        total: int = await db.scalar(total_subq)

        # 4️⃣  Ordenamiento
        if sort:
            field, direction = sort.split("_")
            order_col = getattr(Product, "price" if field == "price" else "name")
            stmt = stmt.order_by(asc(order_col) if direction == "asc" else desc(order_col))
        else:
            # orden por fecha de actualización desc. para mantener “novedades”
            stmt = stmt.order_by(desc(Product.modified))

        # 5️⃣  Paginación
        stmt = stmt.offset((page - 1) * limit).limit(limit)

        # 6️⃣  Ejecución y serialización
        result = await db.execute(stmt)
        rows = result.all()                      # ← cambia aquí

        products = []
        for prod, webpage, store_name in rows:
            data = ProductRead.model_validate(prod, from_attributes=True).model_dump(exclude_none=True)
            data.update(webpage=webpage, store_name=store_name)
            products.append(ProductWithStore(**data))
            print(ProductWithStore(**data))

        return ProductsPage(
            products=products,
            total=total,
            page=page,
            pageSize=limit,
            totalPages=(total + limit - 1) // limit,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/{product_id}", response_model=ProductWithStore)
async def get_product_detail(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Devuelve el producto `product_id` con los campos extra:
    - webpage  (Store.webpage)
    - store_name (Store.name)
    """
    stmt = (
        select(
            Product,
            Store.webpage.label("webpage"),
            Store.name.label("store_name"),
        )
        .join(Product.link)                 # Product → Link
        .join(Link.store)                   # Link → Store
        .options(                           # evita N+1
            joinedload(Product.link).joinedload(Link.store)
        )
        .where(
            Product.id == product_id,
            Product.deleted.is_(False),     # ← solo productos activos
        )
    )

    result = await db.execute(stmt)
    row = result.first()                    # None si no existe

    if row is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    prod, webpage, store_name = row
    base = ProductRead.model_validate(prod, from_attributes=True).model_dump(exclude_none=True)
    base.update(webpage=webpage, store_name=store_name)
    return ProductWithStore(**base)
