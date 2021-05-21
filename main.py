import math
from typing import List

import arcade
from tkinter import *


class Block:
    def __init__(self, x: float, y: float, r: float):
        self.x = x
        self.y = y
        self.r = r

    def __repr__(self) -> str:
        return f'<Block {self.x}/{self.y}/{self.r}>'


class Point:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f'<{super().__repr__()} {self.x}/{self.y}>'


class EndPoint(Point):
    begin: bool = False
    segment: 'Segment' = None
    angle: float = 0.0
    visualize: bool = False

    def __repr__(self) -> str:
        return f'<{super().__repr__()} {self.begin}/{self.angle}'


class Segment:
    p1: EndPoint
    p2: EndPoint
    d: float

    @staticmethod
    def new(p1, p2, d):
        self = Segment()
        p1.segment = self
        p1.visualize = True
        p2.segment = self
        p2.visualize = True

        self.p1 = p1
        self.p2 = p2
        self.d = d
        return self

    def __repr__(self) -> str:
        s = super().__repr__() + '\n'
        s += f'   p1: {self.p1}\n'
        s += f'   p2: {self.p2}\n'
        return str(s)


class Visibility:
    def __init__(self):
        self.segments: List[Segment] = []
        self.endpoints: List[EndPoint] = []
        self.center = Point(0.0, 0.0)

        #сегменти, які використовуються при проходжені променя
        self.open: List[Segment] = []

        # точки які утворюють видимий полігон
        self.output: List[Point] = []

    # границі вікна
    def _loadEdgeOfMap(self, size: int, margin: int):
        self.addSegment(margin, margin, margin, size - margin)
        self.addSegment(margin, size - margin, size - margin, size - margin)
        self.addSegment(size - margin, size - margin, size - margin, margin)
        self.addSegment(size - margin, margin, margin, margin)


    def loadMap(self, size: int, margin: int, blocks: List[Block], walls: List[Segment]):
        self.segments.clear()
        self.endpoints.clear()
        self._loadEdgeOfMap(size, margin)

        for block in blocks:
            x = block.x
            y = block.y
            r = block.r
            self.addSegment(x - r, y - r, x - r, y + r)
            self.addSegment(x - r, y + r, x + r, y + r)
            self.addSegment(x + r, y + r, x + r, y - r)
            self.addSegment(x + r, y - r, x - r, y - r)

        for wall in walls:
            self.addSegment(wall.p1.x, wall.p1.y, wall.p2.x, wall.p2.y)

    def addSegment(self, x1: float, y1: float, x2: float, y2: float):
        segment = Segment()

        p1: EndPoint = EndPoint(x1, y1)
        p1.segment = segment
        p1.visualize = True

        p2: EndPoint = EndPoint(x2, y2)
        p2.segment = segment
        p2.visualize = False

        segment.p1 = p1
        segment.p2 = p2
        segment.d = 0.0

        self.segments.append(segment)
        self.endpoints.append(p1)
        self.endpoints.append(p2)

    #задаємо головну точку та рахуємо кути між іншими точками
    def setLightLocation(self, x: float, y: float):
        self.center.x = x
        self.center.y = y

        for segment in self.segments:
            dx = 0.5 * (segment.p1.x + segment.p2.x) - x
            dy = 0.5 * (segment.p1.y + segment.p2.y) - y
            segment.d = dx * dx + dy * dy

            segment.p1.angle = math.atan2(segment.p1.y - y, segment.p1.x - x)
            segment.p2.angle = math.atan2(segment.p2.y - y, segment.p2.x - x)

            dAngle = segment.p2.angle - segment.p1.angle
            if dAngle <= -math.pi:
                dAngle += 2 * math.pi
            if dAngle > math.pi:
                dAngle -= 2 * math.pi
            segment.p1.begin = (dAngle > 0.0)
            segment.p2.begin = not segment.p1.begin

    @staticmethod
    def _endpoint_key(a: EndPoint) -> tuple:
        return a.angle, not a.begin

    # повертає Тру, якщо точка "лівіше" вектора
    @staticmethod
    def leftOf(s: Segment, p: Point) -> bool:
        cross = (s.p2.x - s.p1.x) * (p.y - s.p1.y) - (s.p2.y - s.p1.y) * (p.x - s.p1.x)
        return cross < 0

    @staticmethod
    def interpolate(p: Point, q: Point, f: float) -> Point:
        return Point(p.x * (1 - f) + q.x * f, p.y * (1 - f) + q.y * f)


    def _segment_in_front_of(self, a: Segment, b: Segment, relativeTo: Point) -> bool:
        A1 = self.leftOf(a, self.interpolate(b.p1, b.p2, 0.01))
        A2 = self.leftOf(a, self.interpolate(b.p2, b.p1, 0.01))
        A3 = self.leftOf(a, relativeTo)
        B1 = self.leftOf(b, self.interpolate(a.p1, a.p2, 0.01))
        B2 = self.leftOf(b, self.interpolate(a.p2, a.p1, 0.01))
        B3 = self.leftOf(b, relativeTo)

        if B1 == B2 and B2 != B3:
            return True
        if A1 == A2 and A2 == A3:
            return True
        if A1 == A2 and A2 != A3:
            return False
        if B1 == B2 and B2 == B3:
            return False

        return False


    # пошук видимих полігонів у вигляді трикутників
    def sweep(self, maxAngle: float = 360.0):
        self.output = []  #точки кінцевих трикутників
        self.endpoints.sort(key=self._endpoint_key)

        self.open.clear()
        begin_angle = 0.0

        for turn in range(2):
            for p in self.endpoints:
                if turn == 1 and p.angle > maxAngle:
                    break

                current_old = self.open[0] if self.open else None

                if p.begin:
                    for i, seg in enumerate(self.open):
                        if self._segment_in_front_of(p.segment, seg, self.center):
                            continue
                        else:
                            self.open.insert(i, p.segment)
                            break
                    else:
                        self.open.append(p.segment)

                else:
                    if p.segment in self.open:
                        self.open.remove(p.segment)

                current_new = None if not self.open else self.open[0]
                if current_old != current_new:
                    if turn == 1:
                        self.addTriangle(begin_angle, p.angle, current_old)

                    begin_angle = p.angle

    def lineIntersection(self, p1: Point, p2: Point, p3: Point, p4: Point) -> Point:
        n1 = ((p4.x - p3.x) * (p1.y - p3.y) - (p4.y - p3.y) * (p1.x - p3.x))
        n2 = ((p4.y - p3.y) * (p2.x - p1.x) - (p4.x - p3.x) * (p2.y - p1.y))
        s = n1 / n2
        return Point(p1.x + s * (p2.x - p1.x), p1.y + s * (p2.y - p1.y))

    def addTriangle(self, angle1: float, angle2: float, segment: Segment):
        p1: Point = self.center
        p2: Point = Point(self.center.x + math.cos(angle1), self.center.y + math.sin(angle1))

        p3: Point = Point(0.0, 0.0)
        p4: Point = Point(0.0, 0.0)

        if segment is not None:
            # Зупинка рикутника на відрізку, що перетинається
            p3.x = segment.p1.x
            p3.y = segment.p1.y
            p4.x = segment.p2.x
            p4.y = segment.p2.y
        else:
            # Зупинка в точкі
            p3.x = self.center.x + math.cos(angle1)
            p3.y = self.center.y + math.sin(angle1)
            p4.x = self.center.x + math.cos(angle2)
            p4.y = self.center.y + math.sin(angle2)

        pBegin = self.lineIntersection(p3, p4, p1, p2)

        p2.x = self.center.x + math.cos(angle2)
        p2.y = self.center.y + math.sin(angle2)
        pEnd = self.lineIntersection(p3, p4, p1, p2)

        self.output.append(pBegin)
        self.output.append(pEnd)


class Dynamic(arcade.Window):

    def __init__(self):
        super().__init__(height=800)
        self.vis = Visibility()
        self.dirty = True

        self.blocks = [
            Block(200, 300, 50),
            Block(100, 200, 30),
            Block(400, 300, 70),
            Block(600, 200, 50),
            Block(300, 550, 50),
        ]
        self.walls = [
            Segment.new(EndPoint(700, 700), EndPoint(750, 750), 0.0),
            Segment.new(EndPoint(550, 700), EndPoint(750, 750), 0.0),
            Segment.new(EndPoint(700, 700), EndPoint(550, 700), 0.0),
        ]

        self.vis.loadMap(800, 0, self.blocks, self.walls)
        self.vis.setLightLocation(400, 400)


    def on_update(self, delta_time: float):
        if self.dirty:
            old = self.vis.output
            try:
                self.vis.sweep()
            except Exception as e:
                print(e)
                self.vis.output = old
            self.dirty = False

    def on_draw(self):
        arcade.start_render()

        ends = zip(self.vis.output[::2], self.vis.output[1::2])
        for p1, p2 in ends:
            arcade.draw_triangle_filled(
                self.vis.center.x, self.vis.center.y,
                p1.x, p1.y,
                p2.x, p2.y,
                color=(0, 100, 100)
            )

            arcade.draw_line(
                self.vis.center.x, self.vis.center.y,
                p1.x, p1.y,
                color=(168, 18, 18)
            )

            arcade.draw_line(
                self.vis.center.x, self.vis.center.y,
                p2.x, p2.y,
                color=(168, 18, 18)
            )

            arcade.draw_line(
                p1.x, p1.y,
                p2.x, p2.y,
                (255, 255, 49),
                5
            )

        for i, block in enumerate(self.blocks):
            arcade.draw_rectangle_filled(block.x, block.y, block.r * 2, block.r * 2, (255, 0, 0))
            arcade.draw_text(str(i), block.x, block.y, color=(0, 0, 0))

        for line in self.walls:
            arcade.draw_line(line.p1.x, line.p1.y, line.p2.x, line.p2.y, (0, 0, 255), 2)

        arcade.draw_circle_filled(self.vis.center.x, self.vis.center.y, 5, (242, 240, 140))

    def on_mouse_motion(self, x: float, y: float, dx: float, dy: float):
        self.vis.setLightLocation(round(x), round(y))
        self.dirty = True

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        input = InputWindow()
        input.run(self.blocks)

        self.vis.loadMap(800, 0, self.blocks, self.walls)


class InputWindow():

    def run(self, blocks):
        self.window = Tk()
        self.window.geometry('200x150')
        self.window.title("Creating block")
        self.enterDataBlock(blocks)

        self.window.mainloop()



    def enterDataBlock(self, blocks):
        x_float = StringVar(self.window)
        y_float = StringVar(self.window)
        r_float = StringVar(self.window)

        x = Label(self.window, text="x : ").grid(row = 0, column = 0)
        y = Label(self.window, text="y : ").grid(row = 1, column = 0)
        r = Label(self.window, text="r : ").grid(row = 2, column = 0)

        in_x = Entry(self.window, textvariable = x_float). grid(row = 0, column = 1)
        in_y = Entry(self.window, textvariable = y_float ). grid(row = 1, column = 1)
        in_r = Entry(self.window, textvariable = r_float). grid(row = 2, column = 1)

        def clicked():
            blocks.append(Block(float(x_float.get()), float(y_float.get()), float(r_float.get())))
            self.window.destroy()

        btn_subm = Button(self.window, text="Submit", command=clicked).grid(row=4, column=1)



if __name__ == '__main__':
    d = Dynamic()
    arcade.run()

