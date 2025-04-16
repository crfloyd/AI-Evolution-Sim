import numpy as np

class NeuralNetwork:
    def __init__(self, input_size, hidden_size=6, output_size=2):
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.output_size = output_size

        # Xavier init
        self.w1 = np.random.randn(hidden_size, input_size) * np.sqrt(1 / input_size)
        self.b1 = np.zeros((hidden_size, 1))
        self.w2 = np.random.randn(output_size, hidden_size) * np.sqrt(1 / hidden_size)
        self.b2 = np.zeros((output_size, 1))

    def activate(self, x):
        return np.tanh(x)

    def forward(self, input_array):
        x = np.array(input_array).reshape(-1, 1)  # column vector
        h = self.activate(self.w1 @ x + self.b1)
        o = self.activate(self.w2 @ h + self.b2)
        return o.flatten()  # output as [angular_velocity, speed]
