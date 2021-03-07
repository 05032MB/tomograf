import skimage.draw, skimage.io
import numpy as np
from abc import ABC, abstractmethod

class AbstractTomograf(ABC):
    def __init__(self, receiver_count, angular_dist, scans_no = 180):
        if receiver_count < 1:
            raise ValueError("Invalid number of beam receivers.")
        if angular_dist < 0:
            raise ValueError("Angular distance cannot be negative")
        if scans_no <= 0:
            raise ValueError("Number of scans has to be a positive number")

        self.receiver_count = receiver_count
        self.angular_dist = angular_dist
        self.scans_no = scans_no
        self.step = 360 / scans_no
        self.rotation = 0

    def tick(self):
        self.rotation += self.step % 360;

    def get_receiver_pos(self, radius, receiver_no):
        x = radius * np.cos(np.pi + np.deg2rad(self.rotation - self.angular_dist / 2 + receiver_no * self.angular_dist/(self.receiver_count - 1) )  )
        y = radius * np.sin(np.pi + np.deg2rad(self.rotation - self.angular_dist / 2 + receiver_no * self.angular_dist/(self.receiver_count - 1) )  )

        return (x, y)

    def get_receivers(self, radius):
        return [self.get_receiver_pos(radius, x) for x in np.arange(0, self.receiver_count - 1) ]

    #def receiver_iter(self, radius):
    #    i = 0

    #    while i < self.receiver_count:
    #        yield self.get_receiver_pos(radius, i)
    #        i+=1

    @abstractmethod
    def get_emitter_pos(self, radius, emitter_no):
        pass

    #@abstractmethod
    #def emitter_iter(self, radius):
    #    pass

    #def beams_iter(self, radius):
    #    for em, rc in zip(self.emitter_iter(radius), self.receiver_iter(radius)):
    #        yield skimage.draw.line_nd(em, rc)

    def get_beams(self, radius):
        beams = []
        for em, rc in zip(self.get_emitters(radius), self.get_receivers(radius)):
            beams.append(skimage.draw.line_nd(em, rc))
        return beams

    def construct_sinogram_frame(self, data):
        height, width = data.shape
        radius = np.sqrt(height**2 + width**2)/2
        frame = []
        beams = self.get_beams(radius)

        for beam in beams:
            def translate(beam, move):
                return [int(np.round(x + move / 2)) for x in beam]

            beams_x = translate(beam[1], height)
            beams_y = translate(beam[0], width)

            beam_translated = np.array(np.column_stack([beams_x, beams_y]))

            # https://thispointer.com/delete-elements-from-a-numpy-array-by-value-or-conditions-in-python/
            beam_translated = beam_translated[
                (beam_translated[:, 0] >= 0 )   & (beam_translated[:, 1] >= 0) &
                (beam_translated[:, 0] < width) & (beam_translated[:, 1] < height)
            ]

            #data[(beam_translated[:, 1], beam_translated[:, 0] )] = 1
            #skimage.io.imshow(data)
            #skimage.io.show()

            frame.append(np.mean(data[ (beam_translated[:, 1], beam_translated[:, 0] ) ]))

        return frame

    def construct_sinogram(self, data):
        i = 0
        frames = []
        while i < self.scans_no:
            frames.append(self.construct_sinogram_frame(data))
            self.tick()
            i+=1
            print("skan: {0}/{1}".format(i, self.scans_no), end = "\r")
        
        return frames

    def __str__(self):
        return ','.join([str(x) for x in [self.receiver_count, self.angular_dist, self.step] ])


class OneEmitterTomograf(AbstractTomograf):
    def __init__(self, *args, **kwargs):
        super(OneEmitterTomograf, self).__init__(*args, **kwargs)
        self.emitter_count = 1

    def get_emitter_pos(self, radius):
        x = radius * np.cos(np.deg2rad(self.rotation))
        y = radius * np.sin(np.deg2rad(self.rotation))
        return (x,y)

    def get_emitters(self, radius):
        return [self.get_emitter_pos(radius) for x in np.arange(0, self.receiver_count - 1) ]
    
    #def emitter_iter(self, radius):
    #    em = self.get_emitter_pos(radius)
    #    i = 0

    #    while i < self.receiver_count:
    #        yield em
    #        i+=1