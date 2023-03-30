# Copyright (c) Facebook, Inc. and its affiliates. All rights reserved.

import logging
from typing import List, Optional

import torch
from reagent.models.fully_connected_network import FullyConnectedNetwork
from reagent.models.linear_regression import batch_quadratic_form, LinearRegressionUCB
from torch import nn

logger = logging.getLogger(__name__)


class DeepRepresentLinearRegressionUCB(LinearRegressionUCB):
    """
    It is a multiple layer regression model that output UCB score.
    The first N layers are trainable by torch optimizer().
    The last layer is the traditional LinUCB, and it is not updated by optimizer,
        but still will be updated by matrix computations.

    Example :
        Features(dim=9) --> deep_represent_layers --> Features(dim=3) --> LinUCB --> ucb score

        DeepRepresentLinUCBTrainer(
        (scorer): DeepRepresentLinearRegressionUCB(
            (deep_represent_layers): FullyConnectedNetwork(
            (dnn): Sequential(
                (0): Linear(in_features=9, out_features=6, bias=True)
                (1): ReLU()
                (2): Linear(in_features=6, out_features=3, bias=True)
                (3): Identity()
            )
            )
        )
        (loss_fn): MSELoss()
        )
    """

    def __init__(
        self,
        input_dim: int,  # raw feature
        sizes: List[int],  # MLP hidden layers of the deep_represent module
        activations: List[str],
        *,
        l2_reg_lambda: float = 1.0,
        ucb_alpha: float = 1.0,
        gamma: float = 1.0,
        use_batch_norm: bool = False,
        dropout_ratio: float = 0.0,
        normalize_output: bool = False,
        use_layer_norm: bool = False,
        mlp_layers: Optional[nn.Module] = None,
    ):
        super().__init__(
            input_dim=sizes[-1],
            l2_reg_lambda=l2_reg_lambda,
            ucb_alpha=ucb_alpha,
            gamma=gamma,
        )

        assert input_dim > 0, "input_dim must be > 0, got {}".format(input_dim)
        assert sizes[-1] > 0, "Last layer size must be > 0, got {}".format(sizes[-1])
        assert len(sizes) == len(
            activations
        ), "The numbers of sizes and activations must match; got {} vs {}".format(
            len(sizes), len(activations)
        )

        self.raw_input_dim = input_dim  # input to DeepRepresent
        if mlp_layers is None:
            self.deep_represent_layers = FullyConnectedNetwork(
                [input_dim] + sizes,
                activations,
                use_batch_norm=use_batch_norm,
                dropout_ratio=dropout_ratio,
                normalize_output=normalize_output,
                use_layer_norm=use_layer_norm,
            )
        else:
            self.deep_represent_layers = mlp_layers  # use customized layer

        self.pred_u = torch.Tensor()
        self.pred_sigma = torch.Tensor()
        self.mlp_out = torch.Tensor()

    def input_prototype(self) -> torch.Tensor:
        return torch.randn(1, self.raw_input_dim)

    def forward(
        self, inp: torch.Tensor, ucb_alpha: Optional[float] = None
    ) -> torch.Tensor:
        """
        Pass raw input to mlp.
        This mlp is trainable to optimizer, i.e., will be updated by torch optimizer(),
            then output of mlp is passed to a LinUCB layer.
        """

        self.mlp_out = self.deep_represent_layers(
            inp
        )  # preprocess by DeepRepresent module before fed to LinUCB layer

        if ucb_alpha is None:
            ucb_alpha = self.ucb_alpha
        self.pred_u = torch.matmul(self.mlp_out, self.coefs)
        if ucb_alpha != 0:
            self.pred_sigma = torch.sqrt(
                batch_quadratic_form(self.mlp_out, self.inv_avg_A)
                / torch.clamp(self.sum_weight, min=0.00001)
            )
            pred_ucb = self.pred_u + ucb_alpha * self.pred_sigma
        else:
            pred_ucb = self.pred_u
        # trainer needs pred_u and mlp_out to update parameters
        return pred_ucb

    def forward_inference(
        self, inp: torch.Tensor, ucb_alpha: Optional[float] = None
    ) -> torch.Tensor:
        mlp_out = self.deep_represent_layers(inp)
        return super().forward_inference(mlp_out)
