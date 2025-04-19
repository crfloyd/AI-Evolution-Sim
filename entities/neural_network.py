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
    
    
    def copy_with_mutation(self, mutation_rate=0.05):
        clone = NeuralNetwork(self.input_size, self.hidden_size, self.output_size)
        clone.w1 = self.w1 + np.random.randn(*self.w1.shape) * mutation_rate
        clone.b1 = self.b1 + np.random.randn(*self.b1.shape) * mutation_rate
        clone.w2 = self.w2 + np.random.randn(*self.w2.shape) * mutation_rate
        clone.b2 = self.b2 + np.random.randn(*self.b2.shape) * mutation_rate
        return clone

