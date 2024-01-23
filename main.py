import json
import os
import random
import re
import time
from  urllib.parse import unquote
from pathlib import Path

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service

from data.data import RECIPE_IDS, FOOD_INGREDIENT_LIST

options = Options()
options.set_preference("browser.download.folderList",2)
options.set_preference("browser.download.manager.showWhenStarting", False)
options.set_preference("browser.download.dir",f"{os.getcwd()}/Downloads")
ff_svc = Service(executable_path="/snap/bin/geckodriver")
#options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream,application/vnd.ms-excel")
# driver = webdriver.Firefox(executable_path=r'C:/Users/Mack/AppData/Local/Programs/Python/Python38-32/geckodriver-v0.27.0-win64/geckodriver.exe', options=options)


URL_PREFIX = "https://www.crock-pot.com/on/demandware.store/Sites-crockpot-Site/default/Content-Show?cid="
max_doc_cnt = 500
FOOD_INGREDIENT_SET = set(FOOD_INGREDIENT_LIST)

MISSING_INGREDIENT_LIST = []

def download_pages():
    ff = webdriver.Firefox(options=options, service=ff_svc)
    download_cnt = 0
    for recipe_id_raw in RECIPE_IDS:
        recipe_id = unquote(recipe_id_raw)
        ff.get(URL_PREFIX + recipe_id_raw)
        with (Path(__name__).parent / "out_html" / f"{recipe_id}.html").open(mode="w") as f:
            f.write(ff.page_source)
        time.sleep(2 + random.randint(1, 3))
        download_cnt = download_cnt + 1
        if download_cnt >= max_doc_cnt:
            break
    ff.close()


def parse_ingredient_tags(ordered_ingredients):
    tagged_ingredients = []
    for ingredient in ordered_ingredients:
        tags = []
        for an_ingredient in FOOD_INGREDIENT_LIST:
            ingredient_ = an_ingredient.lower()
            if ingredient_ in ingredient[1].lower() or f"{ingredient_}s" in ingredient[1].lower():
                tags.append(ingredient_)

        if not tags:
            missing_ingredient = {"ingredient": ingredient[1], "terms": re.sub(r'[0-9]+', '',re.sub(r'[^\w\s]+', '', ingredient[1].lower())).split()}
            # print(missing_ingredient)
            MISSING_INGREDIENT_LIST.append(missing_ingredient)

        tagged_ingredients.append((ingredient[0], tags))

    return tagged_ingredients


def parse_pages():
    doc_cnt = 0
    out_json_path = Path(__name__).parent / "out_json"
    if not out_json_path.exists():
        out_json_path.mkdir()

    all_recipes = []

    for recipe_id_raw in RECIPE_IDS:
        recipe_id = unquote(recipe_id_raw)
        out_html_path = Path(__name__).parent / "out_html" / f"{recipe_id}.html"
        with (out_html_path).open(mode="r") as f:
            p = BeautifulSoup("\n".join(f.readlines()), 'html.parser')
            ingredient_elem = p.select('ul.ingredient-list li') # (By.XPATH, '//ul[contains(@class, "ingredient-list")]')
            instructions_elem = p.select('div.instructions ol li') # (By.XPATH, '//div[contains(@class, "instructions")]')
            if not len(ingredient_elem):
                ingredient_elem =  p.select('div.instructions ul li')

            if not len(ingredient_elem):
                ingredient_elem =  p.select('div.instructions li')

            ordered_ingredients_raw = html_list_items_to_str_list(ingredient_elem)
            ordered_instructions = html_list_items_to_str_list(instructions_elem)

            instructions_text_set = {_[1] for _ in ordered_instructions}

            ordered_ingredients = []
            # reduce ingredients
            for idx, _ in enumerate(ordered_ingredients_raw):
                if _[1] not in instructions_text_set:
                    ordered_ingredients.append(_)

            recipe = {
                "id": recipe_id,
                "name": recipe_id.replace("-", " "),
                "ingredients": ordered_ingredients,
                "ingredient_tags": parse_ingredient_tags(ordered_ingredients),
                "instructions": ordered_instructions,
            }

            if not len(recipe["ingredients"]) or not len(recipe["instructions"]):
                print(f"Warn: {recipe}")

            # with (out_json_path / f"{recipe_id}.json").open(mode="w") as of:
            #     of.write(json.dumps(recipe, indent=2))

            all_recipes.append(recipe)

        doc_cnt = doc_cnt + 1
        if doc_cnt >= max_doc_cnt:
            break

    with (out_json_path / f"_all.json").open(mode="w") as of:
        of.write(json.dumps(all_recipes, indent=2))

    with (out_json_path / f"_missing_ingredients.json").open(mode="w") as of:
        # print(f"{len(MISSING_INGREDIENT_LIST)} ingredients not recognized")
        of.write(json.dumps(MISSING_INGREDIENT_LIST, indent=2))


def html_list_items_to_str_list(html_elems):
    return [(idx, _.text.replace("Crock-", "").replace("Crock", "").replace("crock", "")) for idx, _ in enumerate(html_elems)]


def process_ingredients():
    in_json_path = Path(__name__).parent / "out_json"
    with (in_json_path / f"_all.json").open(mode="r") as f:
        recipes = json.loads(f.read())
        for recipe in recipes:
            print(recipe)
            break


if __name__ == '__main__':
    # download_pages()
    # parse_pages()
    process_ingredients()
