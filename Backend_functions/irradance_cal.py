from dataclasses import dataclass



@dataclass
class LightField:
    G_dir:float
    G_albedo:float
    n:float

    G_diff:float=0.0
    G_total:float=0.0

    def compute(self):
        if not (0.0 <=self.n<1.0):
            raise ValueError ("n must be between 0 and 1")
        self.G_diff=self.n*(self.G_dir+self.G_albedo)
        self.G_total=self.G_dir+self.G_albedo+self.G_diff
        return self


