from PyQt5.QtGui import QImage

from PyQt5.QtCore import QPoint, QRect

import numpy as np
import numpy.typing as npt


if np is not None:
    def get_bounding_box(img: QImage) -> QRect:
        def find_nonwhite_row(array: npt.NDArray[np.int_], backward: bool) -> int:
            r = (lambda x: reversed(x) if backward else x)(range(array.shape[0]))
            for n in r:
                if np.mean(array[n]) < 250:
                    return n
            return r.stop # type: ignore

        img = img.convertToFormat(QImage.Format.Format_RGB32)
        b = img.constBits()
        h, w = img.height(), img.width()
        b.setsize(h * w * 4)
        arr_row = np.array(b).reshape((h, w, 4))
        arr_col = arr_row.transpose(1, 0, 2)
        return QRect(QPoint(find_nonwhite_row(arr_col, False),
                            find_nonwhite_row(arr_row, False)),
                     QPoint(find_nonwhite_row(arr_col, True),
                            find_nonwhite_row(arr_row, True)))

else:
    def get_bounding_box(img: QImage) -> QRect:
        return QRect(0, 0, 0, 0)
