import os
import pickle

import cv2
import numpy as np
from ml.extract_tables import load_train_data
from utils.display_utils import pdf_to_img


def build_im_data(train_pdf, tables_train, im_shape):
    X_train = np.zeros((tables_train.shape[0], im_shape, im_shape))
    train_pdf_names = [name.rstrip() for name in open(train_pdf).readlines()]
    for j, table_data in enumerate(tables_train[90:95]):
        if j % 100 == 0:
            print "{} tables processed out of {}".format(j, tables_train.shape[0])
        pdf_file = train_pdf_names[table_data[0]]
        img = pdf_to_img(os.environ['DATAPATH'] + pdf_file, table_data[1], table_data[2], table_data[3])
        top, left, bottom, right = table_data[-4:]
        right = min(table_data[2], right)
        bottom = min(table_data[3], bottom)
        top = max(0, top)
        left = max(0, left)
        img.crop(left, top, right, bottom)
        # img.resize(im_shape, im_shape)
        # Tmp fix
        # TODO: directly convert wand to numpy !!!
        with img.convert('png') as converted:
            converted.save(filename='converted.png')
        img = cv2.imread('converted.png', cv2.CV_LOAD_IMAGE_GRAYSCALE)
        img = cv2.resize(img, (im_shape, im_shape))
        X_train[j] = img
        # todo: data augmentation
    return X_train


test_pdf = os.environ['MLPATH'] + 'test.pdf.list.paleo.not.scanned'
train_pdf = os.environ['MLPATH'] + 'train.pdf.list.paleo.not.scanned'
gt_train = os.environ['MLPATH'] + 'gt.train'
gt_test = os.environ['MLPATH'] + 'gt.test'

_, y_train, tables_train = load_train_data(train_pdf, gt_train)
_, y_test, tables_test = load_train_data(test_pdf, gt_test)

# we remove candidates with 0 width of 0 height
idx_to_rm = 1 * (tables_train[:, 4] == tables_train[:, 6]) + 1 * (tables_train[:, 5] == tables_train[:, 7])
tables_train = tables_train[idx_to_rm == 0]
y_train = y_train[idx_to_rm == 0]
idx_to_rm = 1 * (tables_test[:, 4] == tables_test[:, 6]) + 1 * (tables_test[:, 5] == tables_test[:, 7])
tables_test = tables_test[idx_to_rm == 0]
y_test = y_test[idx_to_rm == 0]

# build the train image data
im_shape = 224
# X_train = build_im_data(train_pdf, tables_train, im_shape)
# X_train = X_train.astype('float32')
# X_train /= 255.
# nb_train = X_train.shape[0]
# X_train = X_train.reshape(nb_train, im_shape, im_shape, 1)
# data_train = {}
# data_train['train_im'] = X_train
# data_train['train_labels'] = y_train
# pickle.dump(data_train, open(os.environ['MLPATH'] + 'cv.train.data.pkl', 'wb'))
# build the test image data
X_test = build_im_data(test_pdf, tables_test, im_shape)
X_test = X_test.astype('float32')
X_test /= 255.
nb_test = X_test.shape[0]
X_test = X_test.reshape(nb_test, im_shape, im_shape, 1)
data_test = {}
data_test['test_im'] = X_test
data_test['test_labels'] = y_test
pickle.dump(data_test, open(os.environ['MLPATH'] + 'cv.test.data.pkl', 'wb'))

# train the model
# model = Sequential()
# model.add(Conv2D(32, (3, 3), input_shape=(im_shape, im_shape, 1)))
# model.add(Activation('relu'))
# model.add(MaxPooling2D(pool_size=(2, 2)))
#
# model.add(Conv2D(32, (3, 3)))
# model.add(Activation('relu'))
# model.add(MaxPooling2D(pool_size=(2, 2)))
#
# model.add(Flatten())
# model.add(Dense(1))
# #model.add(Dropout(0.5))
# model.add(Activation('sigmoid'))
#
# model.compile(loss='hinge',optimizer='rmsprop',metrics=['accuracy'])
# #model.compile(loss='binary_crossentropy',optimizer='rmsprop',metrics=['accuracy'])
#
# batch_size = 32
# epochs = 1
# model.fit(X_train, y_train, batch_size=batch_size,epochs=epochs,validation_data=(X_test, y_test))
# score = model.evaluate(X_test, y_test, verbose=0)
# print('Test score:', score[0])
# print('Test accuracy:', score[1])
