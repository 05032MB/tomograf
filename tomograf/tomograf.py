import skimage.draw
import numpy as np
from abc import ABC, abstractmethod
import matplotlib.pyplot as plt

class AbstractTomograf(ABC):
    def __init__(self, receiver_count, angular_dist, scans_no=180):
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

    @abstractmethod
    def get_emitter_pos(self, radius, emitter_no):
        pass

    @abstractmethod
    def get_emitters(self, radius):
        pass

    def get_beams(self, radius):
        return [skimage.draw.line_nd(em, rc) for em, rc in zip(self.get_emitters(radius), self.get_receivers(radius))]

    def load_image(self, data):
        self.data = data
        self.cached_beams = []

    def normalize_image(self, frame):
        max = 1.0 if frame.max() <= 1 else 255
        frame *= max/frame.max()
        return frame

    def construct_sinogram_frame(self):
        height, width = self.data.shape
        radius = np.sqrt(height**2 + width**2)/2
        frame = []
        beams = self.get_beams(radius)
        translated_beams = []

        for beam in beams:
            def translate(beam, move):
                return [int(x + move / 2) for x in beam]

            beams_x = translate(beam[1], height)
            beams_y = translate(beam[0], width)

            beam_translated = np.array(np.column_stack([beams_x, beams_y]))

            # https://thispointer.com/delete-elements-from-a-numpy-array-by-value-or-conditions-in-python/
            beam_translated = beam_translated[
                (beam_translated[:, 0] >= 0 )   & (beam_translated[:, 1] >= 0) &
                (beam_translated[:, 0] < width) & (beam_translated[:, 1] < height)
            ]

            #data[(beam_translated[:, 1], beam_translated[:, 0] )] = 1
            #plt.imshow(frame, cmap='gray')
            #plt.show()

            translated_beams.append(beam_translated)
            frame.append(np.sum(self.data[ (beam_translated[:, 1], beam_translated[:, 0] ) ]))

        self.cached_beams.append(translated_beams)

        return frame

    def construct_sinogram(self):
        i = 0
        frames = []
        while i < self.scans_no:
            frames.append(self.construct_sinogram_frame())
            self.tick()
            i+=1
            print("skan: {0}/{1}".format(i, self.scans_no), end = "\r")

        self.sinogram = frames
        
        frames = self.normalize_image(np.array(frames))
        return frames

    def construct_image(self):
        height, width = self.data.shape
        frame = np.zeros((width, height))

        if not self.cached_beams:
            raise NotImplementedError("You need to construct sinogram from an image first.")

        for scanset, beams in zip(self.sinogram, self.cached_beams):
            for beam_val, beam_translated in zip(scanset, beams):
                frame[(beam_translated[:, 1], beam_translated[:, 0] )] += beam_val
            #plt.imshow(frame, cmap='gray')
            #plt.show()

        frame = self.normalize_image(frame)
        return frame

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