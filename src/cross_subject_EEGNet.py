#!/usr/bin/env python3
# -*- coding: utf-8
#
# Gibran Fuentes-Pineda <gibranfp@unam.mx>
# IIMAS, UNAM
# 2019
#
"""
Script to evaluate EEGNet for single-trial cross-subject P300 detection
"""
import argparse
import sys
import numpy as np
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.utils import to_categorical
from sklearn.model_selection import *
from EEGModels import EEGNet
from utils import *

def evaluate_cross_subject_model(data, labels, modelpath):
    """
    Trains and evaluates EEGNet for each subject in the P300 Speller database
    using random cross validation.
    """
    n_sub = data.shape[0]
    n_ex_sub = data.shape[1]
    n_samples = data.shape[2]
    n_channels = data.shape[3]

    aucs = np.zeros(22)

    data = data.reshape((n_sub * n_ex_sub, n_samples, n_channels))
    labels = labels.reshape((n_sub * n_ex_sub))
    groups = np.array([i for i in range(n_sub) for j in range(n_ex_sub)])

    cv = LeaveOneGroupOut()
    for k, (t, v) in enumerate(cv.split(data, labels, groups)):
        X_train, y_train, X_test, y_test = data[t], labels[t], data[v], labels[v]

        rg = np.random.choice(t, 1)
        sv = groups[t] == groups[rg]
        st = np.logical_not(sv)
        X_train, y_train, X_valid, y_valid = data[t][st], labels[t][st], data[t][sv], labels[t][sv]
        print("Partition {0}: train = {1}, valid = {2}, test = {3}".format(k, X_train.shape, X_valid.shape, X_test.shape))
        print("Groups train = {0}, valid = {1}, test = {2}".format(np.unique(groups[t][st]),
                                                                   np.unique(groups[t][sv]),
                                                                   np.unique(groups[v])))
            
        # channel-wise feature standarization
        sc = EEGChannelScaler()
        X_train = np.swapaxes(sc.fit_transform(X_train)[:, np.newaxis, :], 2, 3)
        X_valid = np.swapaxes(sc.transform(X_valid)[:, np.newaxis, :], 2, 3)
        X_test = np.swapaxes(sc.transform(X_test)[:, np.newaxis, :], 2, 3)
        
        model = EEGNet(2, dropoutRate = 0.25, Chans = 6, Samples = 206)
        print(model.summary())
        model.compile(optimizer = 'adam', loss = 'categorical_crossentropy')

        es = EarlyStopping(monitor = 'val_loss', mode = 'min', patience = 50, restore_best_weights = True)
        model.fit(X_train,
                  to_categorical(y_train),
                  batch_size = 256,
                  epochs = 200,
                  validation_data = (X_valid, to_categorical(y_valid)),
                  callbacks = [es])

        proba_test = model.predict(X_test)
        aucs[k] = roc_auc_score(y_test, proba_test[:, 1])
        print('P{0} -- AUC: {1}'.format(k, aucs[k]))
        
    np.savetxt(modelpath + '/aucs.npy', aucs)

def main():
    """
    Main function
    """
    try:
        parser = argparse.ArgumentParser()
        parser = argparse.ArgumentParser(
            description="Evaluates single-trial cross-subject P300 detection using cross-validation")
        parser.add_argument("datapath", type=str,
                            help="Path for the data of the P300 Speller Database (NumPy file)")
        parser.add_argument("labelspath", type=str,
                            help="Path for the labels of the P300 Speller Database (NumPy file)")
        parser.add_argument("modelpath", type=str,
                            help="Path of the directory where the models are to be saved")
        args = parser.parse_args()

        np.random.seed(1)
        
        data, labels = load_db(args.datapath, args.labelspath)
        evaluate_cross_subject_model(data, labels, args.modelpath)
        
    except SystemExit:
        print('for help use --help')
        sys.exit(2)
        
if __name__ == "__main__":
    main()