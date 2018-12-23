#!/usr/bin/env python3
# -*- coding: utf-8
#
# Gibran Fuentes-Pineda <gibranfp@unam.mx>
# IIMAS, UNAM
# 2018
#
"""
Script to evaluate a ResNet50 architecture for single-trial subject-independent P300 detection using cross-validation
"""
import argparse
import sys
import numpy as np
from tensorflow.keras.callbacks import ModelCheckpoint
from sklearn.model_selection import *
from sklearn.utils import resample, class_weight
from resnet50_conv1d import *
from utils import *

def evaluate_independent_model(data, labels, modelpath):
    """
    Trains and evaluates SimpleConv1D architecture for each subject in the P300 Speller database
    using random cross validation.
    """
    aucs = np.zeros(22)
    data = data.reshape((22 * 2880, 206, data.shape[3]))
    labels = labels.reshape((22 * 2880))
    groups = [i for i in range(22) for j in range(2880)]
    cv = LeaveOneGroupOut()
    for k, (t, v) in enumerate(cv.split(data, labels, groups)):
        X_train, y_train, X_valid, y_valid = data[t], labels[t], data[v], labels[v]
        pos_valid_idx = np.where(y_valid == 1)[0]
        neg_valid_idx = np.where(y_valid == 0)[0]
        usample_neg_valid_idx = np.random.choice(neg_valid_idx, len(pos_valid_idx), replace = False)
        usample_idx = np.concatenate([pos_valid_idx, usample_neg_valid_idx])
        X_valid = X_valid[usample_idx]
        y_valid = y_valid[usample_idx]

        print("Partition {0}: train = {1}, valid = {2}".format(k, X_train.shape, X_valid.shape))
        sample_weights = class_weight.compute_sample_weight('balanced', y_train)

        sc = EEGChannelScaler()
        X_train = sc.fit_transform(X_train)
        X_valid = sc.transform(X_valid)
        
        model = ResNet50(input_shape = (206, X_train.shape[2]))
        model.compile(optimizer = 'adam', loss = 'binary_crossentropy', metrics = ['accuracy'])
        
        model.fit(X_train,
                  y_train,
                  batch_size = 256,
                  sample_weight = sample_weights,
                  epochs = 100,
                  validation_data = (X_valid, y_valid))

        model.save(modelpath + '/s' + str(i) + 'p' + str(k) + '.h5')
        proba_valid = model.predict(X_valid)
        aucs[k] = roc_auc_score(y_valid, proba_valid)
        accuracies[k] = accuracy_score(y_valid, np.round(proba_valid))
        print('AUC: {0} ACC: {1}'.format(aucs[k], accuracies[k]))
    np.savetxt(modelpath + '/aucs_s' + str(i) + '.npy', aucs)
    np.savetxt(modelpath + '/accuracies_s' + str(i) + '.npy', accuracies)

def main():
    """
    Main function
    """
    try:
        parser = argparse.ArgumentParser()
        parser = argparse.ArgumentParser(
            description="Evaluates single-trial subject-independent P300 detection using cross-validation")
        parser.add_argument("datapath", type=str,
                            help="Path for the data of the P300 Speller Database (NumPy file)")
        parser.add_argument("labelspath", type=str,
                            help="Path for the labels of the P300 Speller Database (NumPy file)")
        parser.add_argument("modelpath", type=str,
                            help="Path of the directory where the models are to be saved")
        args = parser.parse_args()
        
        data, labels = load_db(args.datapath, args.labelspath)
        evaluate_independent_model(data, labels, args.modelpath)
        
    except SystemExit:
        print('for help use --help')
        sys.exit(2)
        
if __name__ == "__main__":
    main()