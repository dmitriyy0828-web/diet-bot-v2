"""Сервис для работы с FatSecret API (OAuth 2.0) + Open Food Facts fallback."""
import requests
import base64
from typing import Optional
from src.config import config
from src.database import get_db
from src.models import FoodCache
import logging

logger = logging.getLogger(__name__)


class FatSecretService:
    """Клиент для FatSecret Platform API (OAuth 2.0)."""

    BASE_URL = "https://platform.fatsecret.com/rest/server.api"
    AUTH_URL = "https://oauth.fatsecret.com/connect/token"

    def __init__(self):
        self.client_id = config.FATSECRET_CLIENT_ID
        self.client_secret = config.FATSECRET_CLIENT_SECRET
        self._access_token: Optional[str] = None

    def _get_access_token(self) -> str:
        """Получить access token через Client Credentials flow."""
        if self._access_token:
            return self._access_token

        if not self.client_id or not self.client_secret:
            raise ValueError("FatSecret credentials not configured")

        credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()

        headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "grant_type": "client_credentials",
            "scope": "basic",
        }

        try:
            response = requests.post(self.AUTH_URL, headers=headers, data=data, timeout=10)
            response.raise_for_status()
            token_data = response.json()
            self._access_token = token_data["access_token"]
            return self._access_token
        except Exception as e:
            logger.error(f"Failed to get FatSecret token: {e}")
            raise

    def search_food(self, query: str, max_results: int = 5) -> Optional[dict]:
        """Поиск продукта в FatSecret."""
        try:
            token = self._get_access_token()

            params = {
                "method": "foods.search",
                "search_expression": query,
                "max_results": max_results,
                "format": "json",
                "region": "RU",
            }

            headers = {
                "Authorization": f"Bearer {token}",
            }

            response = requests.get(
                self.BASE_URL,
                params=params,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            foods = data.get("foods", {}).get("food", [])
            if not foods:
                return None

            if isinstance(foods, list):
                food = foods[0]
            else:
                food = foods

            description = food.get("food_description", "")
            nutrients = self._parse_description(description)

            return {
                "name": food.get("food_name", query),
                "calories": nutrients.get("calories", 0),
                "protein": nutrients.get("protein", 0),
                "fat": nutrients.get("fat", 0),
                "carbs": nutrients.get("carbs", 0),
                "fiber": nutrients.get("fiber", 0),
                "fatsecret_food_id": food.get("food_id"),
            }

        except Exception as e:
            logger.error(f"FatSecret search error: {e}")
            return None

    def _parse_description(self, description: str) -> dict:
        """Парсит строку описания FatSecret в нутриенты."""
        result = {"calories": 0, "protein": 0, "fat": 0, "carbs": 0, "fiber": 0}

        try:
            if "Per 100g" in description:
                description = description.split("-", 1)[1] if "-" in description else description

            parts = description.replace("|", ",").split(",")

            for part in parts:
                part = part.strip().lower()
                if "calories" in part or "ккал" in part:
                    val = self._extract_number(part)
                    if val:
                        result["calories"] = val
                elif "protein" in part or "белк" in part:
                    val = self._extract_number(part)
                    if val:
                        result["protein"] = val
                elif "fat" in part and "saturated" not in part:
                    val = self._extract_number(part)
                    if val:
                        result["fat"] = val
                elif "carbs" in part or "carbohydrate" in part:
                    val = self._extract_number(part)
                    if val:
                        result["carbs"] = val

        except Exception as e:
            logger.warning(f"Failed to parse description '{description}': {e}")

        return result

    def _extract_number(self, text: str) -> Optional[float]:
        """Извлекает число из строки."""
        import re

        match = re.search(r"[\d.]+", text.replace(",", "."))
        if match:
            try:
                return float(match.group())
            except ValueError:
                pass
        return None


class OpenFoodFactsService:
    """Fallback сервис через Open Food Facts (без OAuth)."""

    BASE_URL = "https://world.openfoodfacts.org/cgi/search.pl"

    def search_food(self, query: str) -> Optional[dict]:
        """Поиск продукта в Open Food Facts."""
        try:
            params = {
                "search_terms": query,
                "search_simple": 1,
                "action": "process",
                "json": 1,
                "page_size": 1,
            }

            response = requests.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            products = data.get("products", [])
            if not products:
                return None

            product = products[0]
            nutriments = product.get("nutriments", {})

            calories = (
                nutriments.get("energy-kcal_100g")
                or nutriments.get("energy-kcal")
                or (nutriments.get("energy_100g", 0) / 4.184)
            )

            return {
                "name": product.get("product_name", query),
                "calories": round(calories) if calories else 0,
                "protein": nutriments.get("proteins_100g", 0) or nutriments.get("proteins", 0),
                "fat": nutriments.get("fat_100g", 0) or nutriments.get("fat", 0),
                "carbs": nutriments.get("carbohydrates_100g", 0)
                or nutriments.get("carbohydrates", 0),
                "fiber": nutriments.get("fiber_100g", 0) or nutriments.get("fiber", 0),
                "source": "openfoodfacts",
            }

        except Exception as e:
            logger.error(f"Open Food Facts search error: {e}")
            return None


# Глобальные экземпляры
_fatsecret_service: Optional[FatSecretService] = None
_openfoodfacts_service: Optional[OpenFoodFactsService] = None


def get_fatsecret_service() -> Optional[FatSecretService]:
    """Получить или создать сервис FatSecret."""
    global _fatsecret_service
    if _fatsecret_service is None:
        if config.FATSECRET_CLIENT_ID and config.FATSECRET_CLIENT_SECRET:
            _fatsecret_service = FatSecretService()
    return _fatsecret_service


def get_openfoodfacts_service() -> OpenFoodFactsService:
    """Получить или создать сервис Open Food Facts."""
    global _openfoodfacts_service
    if _openfoodfacts_service is None:
        _openfoodfacts_service = OpenFoodFactsService()
    return _openfoodfacts_service


def find_food_in_cache_or_api(food_name: str) -> Optional[dict]:
    """Найти продукт: кеш → FatSecret → Open Food Facts."""
    normalized_name = food_name.lower().strip()

    # ШАГ 1: Ищем в локальном кеше
    with get_db() as db:
        cached = db.query(FoodCache).filter(FoodCache.name == normalized_name).first()

        if cached:
            cached.usage_count += 1
            db.commit()
            logger.info(f"Cache hit for '{food_name}'")
            return cached.to_dict()

    # ШАГ 2: Пробуем FatSecret
    fs_service = get_fatsecret_service()
    if fs_service:
        try:
            api_result = fs_service.search_food(food_name)
            if api_result:
                with get_db() as db:
                    cache_entry = FoodCache(
                        name=normalized_name,
                        calories=api_result["calories"],
                        protein=api_result["protein"],
                        fat=api_result["fat"],
                        carbs=api_result["carbs"],
                        fiber=api_result.get("fiber", 0),
                        source="fatsecret",
                        fatsecret_food_id=api_result.get("fatsecret_food_id"),
                    )
                    db.add(cache_entry)
                    db.commit()
                    logger.info(f"Saved '{food_name}' to cache from FatSecret")
                return api_result
        except Exception as e:
            logger.warning(f"FatSecret failed for '{food_name}': {e}")

    # ШАГ 3: Fallback на Open Food Facts (без сохранения в кеш)
    off_service = get_openfoodfacts_service()
    try:
        off_result = off_service.search_food(food_name)
        if off_result:
            logger.info(f"Found '{food_name}' in Open Food Facts (not cached)")
            return off_result
    except Exception as e:
        logger.error(f"Open Food Facts failed for '{food_name}': {e}")

    logger.warning(f"Food not found: '{food_name}'")
    return None


def calculate_nutrition_for_weight(food_data: dict, grams: int) -> dict:
    """Рассчитать нутриенты для указанного веса."""
    ratio = grams / 100
    return {
        "name": food_data["name"],
        "grams": grams,
        "calories": round(food_data["calories"] * ratio),
        "protein": round(food_data.get("protein", 0) * ratio, 1),
        "fat": round(food_data.get("fat", 0) * ratio, 1),
        "carbs": round(food_data.get("carbs", 0) * ratio, 1),
        "fiber": round(food_data.get("fiber", 0) * ratio, 1),
    }
