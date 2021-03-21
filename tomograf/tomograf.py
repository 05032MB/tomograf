import skimage.draw
import numpy as np
from abc import ABC, abstractmethod
import matplotlib.pyplot as plt
from . import filtering


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

    def setAngle(self, angle):
        self.rotation = angle % 360

    def tick(self):
        self.rotation += self.step % 360

    def get_receiver_pos(self, radius, offx, offy, receiver_no):
        x = radius * np.cos(np.pi + np.deg2rad(
            self.rotation - self.angular_dist / 2 + receiver_no * self.angular_dist / (self.receiver_count - 1)))
        y = radius * np.sin(np.pi + np.deg2rad(
            self.rotation - self.angular_dist / 2 + receiver_no * self.angular_dist / (self.receiver_count - 1)))

        return (offx + x, offy + y)

    def get_receivers(self, radius, offx, offy):
        return [self.get_receiver_pos(radius, offx, offy, x) for x in np.arange(0, self.receiver_count - 1)]

    @abstractmethod
    def get_emitter_pos(self, radius, offx, offy, emitter_no):
        pass

    @abstractmethod
    def get_emitters(self, radius, offx, offy):
        pass

    def get_beams(self, radius, offx, offy):
        return [skimage.draw.line_nd(em, rc) for em, rc in
                zip(self.get_emitters(radius, offx, offy), self.get_receivers(radius, offx, offy))]

    # debug
    def dbg_print_rc_em(self, radius, offx, offy):
        em = np.array(self.get_emitters(radius, offx, offy))
        rc = np.array(self.get_receivers(radius, offx, offy))
        print(em, rc)

        plt.plot(em[:, 0], em[:, 1], 'g.', rc[:, 0], rc[:, 1], 'b.')
        plt.show()

    def load_image(self, data):
        self.data = self.normalize_image(data)
        self.cached_beams = []

        self.height, self.width = self.data.shape
        self.radius = np.sqrt(self.height ** 2 + self.width ** 2) / 2

    def normalize_image(self, frame):
        frame = (frame - frame.min()) / (frame.max() - frame.min())
        return frame

    def filter_beam(self, beam, width, height):
        beams_xx = np.array(beam[0])
        beams_yy = np.array(beam[1])

        # https://thispointer.com/delete-elements-from-a-numpy-array-by-value-or-conditions-in-python/
        mask = (beams_xx[:] >= 0) & (beams_yy[:] >= 0) & (
                beams_xx[:] < width) & (beams_yy[:] < height)

        beams_xx = beams_xx[mask]
        beams_yy = beams_yy[mask]

        return beams_xx, beams_yy

    def construct_sinogram_frame(self, do_cache=False):
        if not hasattr(self, "data"):
            raise ValueError("You need to load image for processing first, with load_image.")

        frame = []
        beams = self.get_beams(self.radius, self.width / 2, self.height / 2)
        translated_beams = []

        for beam in beams:
            (beams_xx, beams_yy) = self.filter_beam(beam, self.width, self.height)

            if do_cache:
                translated_beams.append([beams_yy, beams_xx])

            frame.append(np.sum(self.data[(beams_yy, beams_xx)]))

        if do_cache:
            self.cached_beams.append(translated_beams)

        return frame

    def construct_sinogram(self, enable_filter=True, do_cache=False):
        i = 0
        frames = []
        fil = filtering.get_filter(10)

        if not do_cache:
            self.start_angle = self.rotation

        while i < self.scans_no:
            row = self.construct_sinogram_frame(do_cache)
            if enable_filter:
                row = np.convolve(row, fil, mode='same')
            frames.append(row)
            self.tick()
            i += 1
            print("skan: {0}/{1}".format(i, self.scans_no), end="\r")
        print()

        self.sinogram = frames

        frames = self.normalize_image(np.array(frames))
        return frames

    def __construct_image_frame_no_cache(self, frame, scanset):
        beams = self.get_beams(self.radius, self.width / 2, self.height / 2)

        for (beam_val, beam) in zip(scanset, beams):
            (beams_xx, beams_yy) = self.filter_beam(beam, self.width, self.height)
            frame[(beams_yy, beams_xx)] += beam_val

    def construct_image(self, do_gif=True, gif_step=10):
        if not hasattr(self, "sinogram"):
            raise ValueError("You need to process input image first, by calling construct_sinogram.")

        frame = np.zeros((self.height, self.width))
        gif = []
        i = 1
        if not self.cached_beams:
            print("Rekonstrukcja...")
            self.setAngle(self.start_angle)

            for scanset in self.sinogram:
                self.__construct_image_frame_no_cache(frame, scanset)
                self.tick()

                if do_gif:
                    if (i % gif_step) == 0:
                        gif.append(self.normalize_image(frame))
                i+=1

        else:
            for scanset, beams in zip(self.sinogram, self.cached_beams):
                for beam_val, beam_translated in zip(scanset, beams):
                    frame[(beam_translated[0], beam_translated[1])] += beam_val
                    # plt.imshow(frame, cmap='gray')
                    # plt.show()
                if do_gif:
                    if (i % gif_step) == 0:
                        gif.append(self.normalize_image(frame))
                i+=1

        frame = self.normalize_image(frame)
        MSE = np.mean(np.power(frame - self.data, 2))
        print("MSE: {0}".format(MSE))
        return frame, MSE, gif

    # debug
    def __str__(self):
        return ','.join([str(x) for x in [self.receiver_count, self.angular_dist, self.step]])


class OneEmitterTomograf(AbstractTomograf):
    def __init__(self, *args, **kwargs):
        super(OneEmitterTomograf, self).__init__(*args, **kwargs)
        self.emitter_count = 1

    def get_emitter_pos(self, radius, offx, offy):
        x = radius * np.cos(np.deg2rad(self.rotation))
        y = radius * np.sin(np.deg2rad(self.rotation))
        return (offx + x, offy + y)

    def get_emitters(self, radius, offx, offy):
        return [self.get_emitter_pos(radius, offx, offy) for x in np.arange(0, self.receiver_count - 1)]


class ManyEmitterTomograf(AbstractTomograf):
    def __init__(self, *args, **kwargs):
        super(ManyEmitterTomograf, self).__init__(*args, **kwargs)
        self.emitter_count = self.receiver_count

    def get_emitter_pos(self, radius, offx, offy, receiver_no):
        x = -1 * radius * np.cos(np.pi + np.deg2rad(
            self.rotation - self.angular_dist / 2 + receiver_no * self.angular_dist / (self.receiver_count - 1)))
        y = -1 * radius * np.sin(np.pi + np.deg2rad(
            self.rotation - self.angular_dist / 2 + receiver_no * self.angular_dist / (self.receiver_count - 1)))
        return ((offx + x), (offy + y))

    def get_emitters(self, radius, offx, offy):
        return [self.get_emitter_pos(radius, offx, offy, x) for x in np.arange(0, self.emitter_count - 1)][::-1]
