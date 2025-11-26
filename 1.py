from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties, CollisionRay, CollisionTraverser, CollisionNode, CollisionHandlerQueue, BitMask32
from panda3d.core import Point3, Vec3
from direct.task import Task
from panda3d.core import AmbientLight, DirectionalLight, Vec4
from direct.actor.Actor import Actor
from direct.gui.DirectGui import DirectFrame
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode
import math

class Game(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        #Гравець
        self.player = Actor("models/panda-model",
                            {"walk": "models/panda-walk4"})
        self.player.setScale(0.01)
        self.player.reparentTo(self.render)
        self.player.setPos(0, 0, 10)

        #Земля
        self.ground = loader.loadModel("models/forest/scene.gltf")
        self.ground.reparentTo(render)
        self.ground.setScale(50)
        self.ground.setPos(0, 0, 0)
        self.ground.setHpr(0, 90, 90)

        #3 Скрині
        self.chests = []

        def add_chest(x, y, z):
            chest = loader.loadModel("models/treasure-chest/source/chest-anim/chest-anim.fbx")
            chest.reparentTo(render)
            chest.setScale(0.10)
            chest.setPos(x, y, z)
            chest.setHpr(0, 90, 90)
            self.chests.append(chest)

        add_chest(35, 270, 3)
        add_chest(-40, 440, 3)
        add_chest(70, 70, 3)

        # Колізії землі
        for node in self.ground.findAllMatches("**/+GeomNode"):
            node.node().setIntoCollideMask(BitMask32.bit(1))

        #Промінь
        self.ray = CollisionRay()
        self.ray.setDirection(0, 0, -1)

        self.ray_node = CollisionNode("playerRay")
        self.ray_node.addSolid(self.ray)
        self.ray_node.setFromCollideMask(BitMask32.bit(1))
        self.ray_node.setIntoCollideMask(BitMask32.allOff())
        self.ray_np = render.attachNewNode(self.ray_node)

        self.ray_handler = CollisionHandlerQueue()
        self.cTrav = base.cTrav = CollisionTraverser()
        self.cTrav.addCollider(self.ray_np, self.ray_handler)

        # Клавіші
        self.keys = {"w": False, "s": False, "a": False, "d": False}
        for k in self.keys:
            self.accept(k, self.set_key, [k, True])
            self.accept(k + "-up", self.set_key, [k, False])

        # Камера
        self.disableMouse()
        self.camera_distance = 40
        self.camera_height = 15
        self.camera_angle_h = 0

        #Вікно
        props = WindowProperties()
        props.setSize(1280, 720)  # розмір вікна
        props.setCursorHidden(True)
        self.win.requestProperties(props)
        self.center_mouse()

        # Світло
        ambient = AmbientLight("ambient")
        ambient.setColor(Vec4(0.5, 0.5, 0.6, 1))
        ambient_np = render.attachNewNode(ambient)
        render.setLight(ambient_np)

        sun = DirectionalLight('sun')
        sun.setColor(Vec4(0.5, 0.5, 0.5, 1))
        sun_np = render.attachNewNode(sun)
        sun_np.setHpr(20, -70, 0)
        render.setLight(sun_np)

        #Повідомлення
        self.message_frame = DirectFrame(
            frameColor=(0.5, 0.5, 0.5, 0.7),
            frameSize=(-0.5, 0.5, -0.1, 0.1),
            pos=(0, 0, 0)
        )
        self.message_frame.hide()

        self.treasure_found = 0
        self.treasure_text = OnscreenText(
            text=f"You found {self.treasure_found} treasure chest!",
            pos=(0, 0),
            scale=0.07,
            mayChange=True,
            align=TextNode.ACenter,
            fg=(1, 1, 1, 1),
            parent=self.message_frame
        )

        self.taskMgr.add(self.update, "UpdateTask")
        self.taskMgr.add(self.mouse_update, "MouseTask")
        self.taskMgr.add(self.collect_treasure, "CollectTreasureTask")

        # ----- Музика -----
        self.bg_music = loader.loadMusic('sounds/Caketown 1.mp3')
        self.bg_music.setLoop(True)
        self.bg_music.play()

        self.chest_sound = loader.loadSfx('sounds/treasure sound.mp3')

        self.accept("escape", exit)

        # Стан анімації
        self.is_walking = False

    def set_key(self, key, state):
        self.keys[key] = state

    def center_mouse(self):
        self.win.movePointer(0, int(self.win.getXSize() / 2), int(self.win.getYSize() / 2))

    def update(self, task):
        dt = globalClock.getDt()
        speed = 800 * dt

        moving = False
        if self.keys["w"]:
            self.player.setY(self.player, -speed)
            moving = True
        if self.keys["s"]:
            self.player.setY(self.player, speed)
            moving = True
        if self.keys["a"]:
            self.player.setX(self.player, speed)
            moving = True
        if self.keys["d"]:
            self.player.setX(self.player, -speed)
            moving = True

        if moving and not self.is_walking:
            self.player.loop("walk")
            self.is_walking = True
        elif not moving and self.is_walking:
            self.player.stop()
            self.is_walking = False

        self.player.setH(self.camera_angle_h + 180)

        px, py, pz = self.player.getPos()
        rad = math.radians(self.camera_angle_h)
        cam_x = px + self.camera_distance * math.sin(rad)
        cam_y = py - self.camera_distance * math.cos(rad)

        self.camera.setPos(cam_x, cam_y, pz + self.camera_height)
        self.camera.lookAt(self.player.getPos() + Point3(0, 0, 7))

        px, py, pz = self.player.getPos(render)
        self.ray_np.setPos(px, py, pz + 2)

        if self.ray_handler.getNumEntries() > 0:
            self.ray_handler.sortEntries()
            for entry in self.ray_handler.getEntries():
                hit_z = entry.getSurfacePoint(render).z
                if hit_z < pz:
                    self.player.setZ(hit_z + 0.5)
                    break

        return Task.cont

    def mouse_update(self, task):
        if self.mouseWatcherNode.hasMouse():
            x = self.win.getPointer(0).getX()
            center_x = self.win.getXSize() / 2

            self.camera_angle_h -= (x - center_x) * 0.2
            self.center_mouse()
        return Task.cont

    def collect_treasure(self, task):
        player_pos = self.player.getPos(render)

        for chest in self.chests[:]:
            chest_pos = chest.getPos(render)
            distance = (player_pos - chest_pos).length()

            if distance < 25:
                chest.removeNode()
                self.chests.remove(chest)

                self.chest_sound.play()

                self.treasure_found += 1
                self.treasure_text.setText(str(self.treasure_found) + " chests found")
                self.message_frame.show()
                self.taskMgr.doMethodLater(5, self.hide_message, "hideMessageTask")

        return Task.cont

    def hide_message(self, task):
        self.message_frame.hide()
        return Task.done


game = Game()
game.run()
