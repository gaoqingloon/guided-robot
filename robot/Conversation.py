# -*- coding: utf-8-*-
import time
import uuid
import cProfile
import pstats
import io
import re
import serial
from queue import Queue
from robot.Brain import Brain
from snowboy import snowboydecoder
from robot import logging, ASR, TTS, NLU, AI, Player, config, \
    constants, utils, gps, destination, avoid, Logic, \
    etl, walk_route

logger = logging.getLogger(__name__)


class Node(object):
    """
        123.42160486207,41.771856760044
        (经度，纬度)
    """

    def __init__(self, ang, lng, lat):
        self.ang = ang
        self.lng = lng
        self.lat = lat


class Conversation(object):
    def __init__(self, profiling=False):
        self.reload()
        # 历史会话消息
        self.history = []
        # 沉浸模式，处于这个模式下，被打断后将自动恢复这个技能
        self.matchPlugin = None
        self.immersiveMode = None
        self.isRecording = False
        self.profiling = profiling
        self.onSay = None
        self.hasPardon = False

        self.serial_port = serial.Serial("/dev/ttyUSB0", 9600, timeout=0.5)

        self.robot = avoid.Avoid()  # 实例化避障程序
        self.etl = etl.ETLUtil(ori_file="record_point.txt", des_file="turn.txt", threshold=30.0)
        self.lc = Logic.Logic("turn.txt")
        self.lc_aux = Logic.Logic("turn.txt")
        self.queue = Queue()

    def getHistory(self):
        return self.history

    def interrupt(self):
        if self.player is not None and self.player.is_playing():
            self.player.stop()
            self.player = None
        if self.immersiveMode:
            self.brain.pause()

    def reload(self):
        """ 重新初始化 """
        try:
            self.asr = ASR.get_engine_by_slug(config.get('asr_engine', 'baidu-asr'))
            self.ai = AI.get_robot_by_slug(config.get('robot', 'tuling'))
            self.tts = TTS.get_engine_by_slug(config.get('tts_engine', 'baidu-tts'))
            self.nlu = NLU.get_engine_by_slug(config.get('nlu_engine', 'unit'))
            self.player = None
            self.brain = Brain(self)
            self.brain.printPlugins()
        except Exception as e:
            logger.critical("对话初始化失败：{}".format(e))

    def checkRestore(self):
        if self.immersiveMode:
            self.brain.restore()

    def doResponse(self, query, UUID='', onSay=None):
        self.interrupt()
        self.appendHistory(0, query, UUID)
        if onSay:
            self.onSay = onSay
        if query.strip() == '':
            self.pardon()
            return
        lastImmersiveMode = self.immersiveMode

        if not self.brain.query(query):

            print("destination: ", query)
            # 通过文字查询得到目的地的经纬度
            # des = destination.search(query)
            des = "东北大学汉卿会堂"
            print("des:", des)
            if des is None:
                self.say("没有查询到该位置，请换个位置", True, onCompleted=self.checkRestore)
                time.sleep(5)
                return

            else:
                # 语音与gps模块，避障模块，导航功能等结合

                # 避障模块引脚初始化
                self.robot.init()

                # 1. 保存途经点信息到文件
                # 通过gps模块得到当前的经纬度
                # ori_lng_lat = gps.get_cur_loc_by_gps(self.serial_port)
                # cur_gps = gps.convert(ori_lng_lat)  # 经度,纬度

                # 保存途经点信息到文件
                # walk_route.save_route_points(ori=cur_gps, des=des, save_file="record_point.txt")

                # 2. 提取转弯点文件并保存
                # self.etl.compute_and_save()

                # 3. 路线规划
                self.say("正在为您规划路线！", True, onCompleted=None)
                time.sleep(5)

                # 4. 转弯点放入队列
                self.lc.file_to_queue()  # 转弯点放入队列
                self.lc_aux.file_to_queue()  # 转弯点放入队列
                self.lc_aux.queue.get()  # 丢掉起始点

                self.say("路线规划完成！", True, onCompleted=None)
                time.sleep(5)

                while not self.lc_aux.queue.empty():
                    cal_node_cur = self.lc.queue.get()  # 起始点
                    cal_node_next = self.lc_aux.queue.get()  # 后一个

                    # 不断通过gps模块获取当前坐标
                    while True:
                        self.say("正在为您定位！", True, onCompleted=None)
                        # 通过gps模块得到当前的经纬度
                        ori_lng_lat = gps.get_cur_loc_by_gps(self.serial_port)

                        time.sleep(5)

                        # 经纬度转换
                        cur_gps = gps.convert(ori_lng_lat)

                        # 封装loc_node
                        gps_lng = cur_gps.split(",")[0]
                        gps_lat = cur_gps.split(",")[1].replace("\n", "")
                        print(gps_lng, gps_lat, cal_node_next.lng, cal_node_next.lat)
                        gps_ang = self.lc_aux.calc_util(gps_lng, gps_lat, cal_node_next.lng, cal_node_next.lat)
                        loc_node = Node(gps_ang, gps_lng, gps_lat)

                        # 判停条件
                        if self.lc_aux.get_distance(loc_node, cal_node_next) < 10:
                            if self.lc_aux.queue.qsize() == 0:
                                print("到达目的地")
                                self.say("主人，到达目的地", True, onCompleted=self.checkRestore)
                                time.sleep(5)
                            else:
                                print("到达转弯点，请注意转弯")
                                msg = self.lc_aux.turn_logic(cur_node=cal_node_cur, next_node=cal_node_next)
                                msg = "到达转弯点，" + msg
                                self.say(msg, True, onCompleted=None)
                                time.sleep(5)
                            break

                        # 在每次定位之后，进行障碍物检测
                        # 当前方识别到障碍物时，语音“前方xxx米有障碍物”
                        # xxx米：超声波测距模块
                        # 遇到障碍物躲避：红外避障模块，红外避障可以判断是左侧还是右侧有障碍物
                        msg_ = self.robot.ultrasonic_avoid()
                        while msg_ is not None:
                            # 防止超声波检测到障碍，红外避障没有检测到障碍
                            msg = self.robot.infrared_avoid()
                            if msg:
                                print(msg)
                                self.say(msg, True, onCompleted=None)
                                time.sleep(5)
                            else:
                                print(msg_)
                                self.say(msg_, True, onCompleted=None)
                                time.sleep(5)
                            msg_ = self.robot.ultrasonic_avoid()

                        self.say("前方没有障碍物，请直行", True, onCompleted=None)
                        time.sleep(5)
                        """
                            起点到终点分为多段路，一段路从queue中读取一个转弯点
                            Node 中封装的是，当前节点和前面的角
                        """
                        gps_lng = cur_gps.split(",")[0]
                        gps_lat = cur_gps.split(",")[1].replace("\n", "")
                        gps_ang = self.lc_aux.calc_util(gps_lng, gps_lat, cal_node_next.lng, cal_node_next.lat)
                        loc_node = Node(gps_ang, gps_lng, gps_lat)

                        print(loc_node.lng, loc_node.lat, cal_node_next.lng, cal_node_next.lat)
                        # 执行
                        # 退出逻辑：当前定位与下一个转弯点距离小于5米，
                        msg = "距离下一个转弯点距离为" + str(round(self.lc_aux.get_distance(loc_node, cal_node_next), 1)) + "米"
                        print(msg)
                        self.say(msg, True, onCompleted=None)
                        time.sleep(5)

                        # 行走逻辑：当前位置 和 下一个转弯点 关系
                        msg = self.lc_aux.walk_logic(loc_node=loc_node, next_node=cal_node_next)
                        print(msg)
                        self.say(msg, True, onCompleted=None)
                        print("over")

                        # 每隔15s重新定位
                        time.sleep(15)

        else:
            if lastImmersiveMode is not None and lastImmersiveMode != self.matchPlugin:
                time.sleep(1)
                if self.player is not None and self.player.is_playing():
                    logger.debug('等说完再checkRestore')
                    self.player.appendOnCompleted(lambda: self.checkRestore())
                else:
                    logger.debug('checkRestore')
                    self.checkRestore()

    def doParse(self, query, **args):
        return self.nlu.parse(query, **args)

    def setImmersiveMode(self, slug):
        self.immersiveMode = slug

    def getImmersiveMode(self):
        return self.immersiveMode

    def converse(self, fp, callback=None):
        """ 核心对话逻辑 """
        Player.play(constants.getData('beep_lo.wav'))
        logger.info('结束录音')
        self.isRecording = False
        if self.profiling:
            logger.info('性能调试已打开')
            pr = cProfile.Profile()
            pr.enable()
            self.doConverse(fp, callback)
            pr.disable()
            s = io.StringIO()
            sortby = 'cumulative'
            ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
            ps.print_stats()
            print(s.getvalue())
        else:
            self.doConverse(fp, callback)

    def doConverse(self, fp, callback=None, onSay=None):
        try:
            self.interrupt()
            query = self.asr.transcribe(fp)  # yuyin to text
            # print("query: ", query)
            utils.check_and_delete(fp)
            self.doResponse(query, callback, onSay)
        except Exception as e:
            logger.critical(e)
            utils.clean()

    def appendHistory(self, t, text, UUID=''):
        """ 将会话历史加进历史记录 """
        if t in (0, 1) and text != '':
            if text.endswith(',') or text.endswith('，'):
                text = text[:-1]
            if UUID == '' or UUID == None or UUID == 'null':
                UUID = str(uuid.uuid1())
            # 将图片处理成HTML
            pattern = r'https?://.+\.(?:png|jpg|jpeg|bmp|gif|JPG|PNG|JPEG|BMP|GIF)'
            url_pattern = r'^https?://.+'
            imgs = re.findall(pattern, text)
            for img in imgs:
                text = text.replace(img, '<img src={} class="img"/>'.format(img))
            urls = re.findall(url_pattern, text)
            for url in urls:
                text = text.replace(url, '<a href={} target="_blank">{}</a>'.format(url, url))
            self.history.append({'type': t,
                                 'text': text,
                                 'time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                                 'uuid': UUID})

    def _onCompleted(self, msg):
        if config.get('active_mode', False) and \
                (
                                    msg.endswith('?') or
                                    msg.endswith(u'？') or
                                    u'告诉我' in msg or u'请回答' in msg
                ):
            query = self.activeListen()
            self.doResponse(query)

    def pardon(self):
        if not self.hasPardon:
            self.say("抱歉，刚刚没听清，能再说一遍吗？", onCompleted=lambda: self.doResponse(self.activeListen()))
            self.hasPardon = True
        else:
            self.say("没听清呢")
            self.hasPardon = False

    def say(self, msg, cache=False, plugin='', onCompleted=None):
        """ 说一句话 """
        if self.onSay:
            logger.info('onSay: {}'.format(msg))
            if plugin != '':
                self.onSay("[{}] {}".format(plugin, msg))
            else:
                self.onSay(msg)
            self.onSay = None
        if plugin != '':
            self.appendHistory(1, "[{}] {}".format(plugin, msg))
        else:
            self.appendHistory(1, msg)
        pattern = r'^https?://.+'
        if re.match(pattern, msg):
            logger.info("内容包含URL，所以不读出来")
            return
        voice = ''
        if utils.getCache(msg):
            # 读取缓存
            logger.info("命中缓存，播放缓存语音")
            voice = utils.getCache(msg)
        else:
            try:
                # 重新进行语音识别
                voice = self.tts.get_speech(msg)
                if cache:
                    utils.saveCache(voice, msg)
            except Exception as e:
                logger.error('保存缓存失败：{}'.format(e))
        if onCompleted is None:
            onCompleted = lambda: self._onCompleted(msg)
        self.player = Player.SoxPlayer()
        self.player.play(voice, not cache, onCompleted)

    def activeListen(self, silent=False):
        """ 主动问一个问题(适用于多轮对话) """
        logger.debug('activeListen')
        try:
            if not silent:
                time.sleep(1)
                Player.play(constants.getData('beep_hi.wav'))
            listener = snowboydecoder.ActiveListener(
                [constants.getHotwordModel(config.get('hotword', 'xiaofeng.pmdl'))])
            voice = listener.listen(
                silent_count_threshold=config.get('silent_threshold', 15),
                recording_timeout=config.get('recording_timeout', 5) * 4
            )
            if not silent:
                Player.play(constants.getData('beep_lo.wav'))
            if voice:
                query = self.asr.transcribe(voice)
                utils.check_and_delete(voice)
                return query
        except Exception as e:
            logger.error(e)
            return ''

    def play(self, src, delete=False, onCompleted=None, volume=1):
        """ 播放一个音频 """
        if self.player:
            self.interrupt()
        self.player = Player.SoxPlayer()
        self.player.play(src, delete, onCompleted=onCompleted, volume=volume)
