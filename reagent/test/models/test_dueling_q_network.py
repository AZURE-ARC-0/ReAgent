#!/usr/bin/env python3
# Copyright (c) Facebook, Inc. and its affiliates. All rights reserved.

import logging
import unittest

from reagent.models.dueling_q_network import DuelingQNetwork
from reagent.models.fully_connected_network import FullyConnectedNetwork
from reagent.test.models.test_utils import check_save_load


logger = logging.getLogger(__name__)


class TestDuelingQNetwork(unittest.TestCase):
    def test_discrete_action(self):
        state_dim = 8
        action_dim = 4
        model = DuelingQNetwork(
            action_dim=action_dim,
            embedding=FullyConnectedNetwork(
                layers=[state_dim, 8, 4],
                activations=["relu", "relu"],
                use_batch_norm=True,
            ),
        )
        input = model.input_prototype()
        self.assertEqual((1, state_dim), input.state.float_features.shape)
        # Using batch norm requires more than 1 example in training, avoid that
        model.eval()
        q_values = model(input)
        self.assertEqual((1, action_dim), q_values.q_values.shape)

    def test_save_load_discrete_action(self):
        state_dim = 8
        action_dim = 4
        model = DuelingQNetwork(
            action_dim=action_dim,
            embedding=FullyConnectedNetwork(
                layers=[state_dim, 8, 4],
                activations=["relu", "relu"],
                use_batch_norm=True,
            ),
        )
        expected_num_params, expected_num_inputs, expected_num_outputs = 22, 1, 1
        check_save_load(
            self, model, expected_num_params, expected_num_inputs, expected_num_outputs
        )

    def test_save_load_discrete_action_batch_norm(self):
        state_dim = 8
        action_dim = 4
        model = DuelingQNetwork(
            action_dim=action_dim,
            embedding=FullyConnectedNetwork(
                layers=[state_dim, 8, 4],
                activations=["relu", "relu"],
                use_batch_norm=True,
            ),
        )
        # Freezing batch_norm
        model.eval()
        # Number of expected params is the same because DuelingQNetwork always
        # initialize batch norm layer even if it doesn't use it.
        expected_num_params, expected_num_inputs, expected_num_outputs = 22, 1, 1
        check_save_load(
            self, model, expected_num_params, expected_num_inputs, expected_num_outputs
        )
