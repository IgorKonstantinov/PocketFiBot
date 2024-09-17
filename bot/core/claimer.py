import inspect
import asyncio
#from time import time
from datetime import datetime, time
from urllib.parse import unquote

import random
import aiohttp
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered
from pyrogram.raw.functions.messages import RequestWebView


from bot.config import settings
from bot.utils import logger
from bot.utils.daily import get_daily_reward_task
from bot.exceptions import InvalidSession
from .headers import headers

def is_time_allowed():
    current_time = datetime.now().time()
    if current_time >= time(0, 0) and current_time < time(6, 0):
        return False
    return True


class Claimer:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client

    async def get_tg_web_data(self, proxy: str | None) -> str:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            if not self.tg_client.is_connected:
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            web_view = await self.tg_client.invoke(RequestWebView(
                peer=await self.tg_client.resolve_peer('pocketfi_bot'),
                bot=await self.tg_client.resolve_peer('pocketfi_bot'),
                platform='android',
                from_bot_menu=False,
                url='https://botui.pocketfi.org/mining/'
            ))

            auth_url = web_view.url
            tg_web_data = unquote(
                string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0])

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return tg_web_data

        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error during Authorization: {error}")
            await asyncio.sleep(delay=3)

    async def get_mining_data(self, http_client: aiohttp.ClientSession) -> dict[str]:
        try:
            logger.info(f"{self.session_name} | bot action: [{inspect.currentframe().f_code.co_name}]")
            response = await http_client.get('https://gm.pocketfi.org/mining/getUserMining')
            response.raise_for_status()

            response_json = await response.json()
            mining_data = response_json['userMining']

            return mining_data
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting Profile Data: {error}")
            await asyncio.sleep(delay=3)

    async def send_claim(self, http_client: aiohttp.ClientSession) -> bool:
        try:
            logger.info(f"{self.session_name} | bot action: [{inspect.currentframe().f_code.co_name}]")
            response = await http_client.post('https://gm.pocketfi.org/mining/claimMining', json={})
            response.raise_for_status()
            if response.ok:
                return True
            else:
                return False

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Claiming: {error}")
            await asyncio.sleep(delay=30)
            return False

    async def get_list_of_tasks(self, http_client: aiohttp.ClientSession):
        try:
            logger.info(f"{self.session_name} | bot action: [{inspect.currentframe().f_code.co_name}]")
            response = await http_client.get('https://bot2.pocketfi.org/mining/taskExecuting')
            response.raise_for_status()

            response_json = await response.json()
            #all_tasks_data = response_json.get('tasks')

            return response_json
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting List of tasks: {error}")
            return None

    async def send_claim_daily_reward(self, http_client: aiohttp.ClientSession, day) -> bool:
        try:
            logger.info(f"{self.session_name} | bot action: [{inspect.currentframe().f_code.co_name}]")
            response = await http_client.post('https://bot2.pocketfi.org/boost/activateDailyBoost', json={})
            response.raise_for_status()

            if response.ok:
                response_json = await response.json()
                updated_for_day = int(response_json.get('updatedForDay'))
                if updated_for_day == day:
                    return True
                else:
                    return False
            else:
                return False

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Claiming daily reward: {error}")
            await asyncio.sleep(delay=30)
            return False

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")


    async def run(self, proxy: str | None) -> None:

        while True:
            try:
                # Randomize variables
                random_sleep = random.randint(*settings.RANDOM_SLEEP)
                random_long_sleep = random.randint(*settings.RANDOM_LONG_SLEEP)

                if is_time_allowed():
                    proxy_conn = ProxyConnector().from_url(proxy) if proxy else None
                    http_client = aiohttp.ClientSession(headers=headers, connector=proxy_conn)
                    tg_web_data = await self.get_tg_web_data(proxy=proxy)

                    http_client.headers["telegramRawData"] = tg_web_data
                    headers["telegramRawData"] = tg_web_data

                    mining_data = await self.get_mining_data(http_client=http_client)
                    await asyncio.sleep(delay=random_sleep)

                    last_claim_time = datetime.fromtimestamp(
                        int(str(mining_data['dttmLastClaim'])[:-3])).strftime('%Y-%m-%d %H:%M:%S')
                    claim_deadline_time = datetime.fromtimestamp(
                        int(str(mining_data['dttmClaimDeadline'])[:-3])).strftime('%Y-%m-%d %H:%M:%S')

                    logger.info(f"{self.session_name} | Last claim time: {last_claim_time}")
                    logger.info(f"{self.session_name} | Claim deadline time: {claim_deadline_time}")

                    list_of_tasks = await self.get_list_of_tasks(http_client=http_client)
                    await asyncio.sleep(delay=random_sleep)

                    list_of_tasks_daily_code = list_of_tasks['tasks']['daily']
                    #print(list_of_tasks_daily_code)

                    if list_of_tasks_daily_code:
                        daily_tasks_max_amount, daily_tasks_done_amount, daily_tasks_current_day = get_daily_reward_task(list_of_tasks_daily_code)

                    if daily_tasks_done_amount == daily_tasks_max_amount:
                        logger.info(f"{self.session_name} | Daily reward for day Nr {daily_tasks_current_day + 1} already claimed")
                    else:
                        claimed_daily_reward = await self.send_claim_daily_reward(http_client=http_client,day=daily_tasks_current_day)
                        await asyncio.sleep(delay=random_sleep)

                        if claimed_daily_reward:
                            logger.success(f"{self.session_name} | Successfuly claimed daily reward for day Nr {daily_tasks_current_day + 1}")
                        else:
                            logger.error(f"{self.session_name} | Claiming daily reward for day Nr {daily_tasks_current_day + 1}: FAILED")

                    balance = mining_data['gotAmount']
                    available = mining_data['miningAmount']
                    speed = mining_data['speed']

                    logger.info(f"{self.session_name} | Balance: <c>{balance}</c> | "
                                f"Available: <e>{available:.2f}</e> | Speed: <m>{speed}</m>")

                    if available > 1:
                        status = await self.send_claim(http_client=http_client)
                        await asyncio.sleep(delay=random_sleep)
                        if status:
                            mining_data = await self.get_mining_data(http_client=http_client)
                            await asyncio.sleep(delay=random_sleep)
                            balance = mining_data['gotAmount']
                            logger.success(f"{self.session_name} | Successful claim | "
                                           f"Balance: <c>{balance}</c> (<g>+{available:.2f}</g>)")

                    else:
                        logger.info(f"{self.session_name} | not enough available: {available:.2f}")
                        await http_client.close()

                else:
                    logger.info(f"{self.session_name} | It's time for sleep...")

                logger.info(f"{self.session_name} | Sleep {random_long_sleep}s")
                await asyncio.sleep(delay=random_long_sleep)

            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f"{self.session_name} | Unknown error: {error}")
                await http_client.close()
                await asyncio.sleep(delay=300)


async def run_claimer(tg_client: Client, proxy: str | None):
    try:
        await Claimer(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
