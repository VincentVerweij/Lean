# QUANTCONNECT.COM - Democratizing Finance, Empowering Individuals.
# Lean Algorithmic Trading Engine v2.0. Copyright 2014 QuantConnect Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from clr import AddReference
AddReference("System")
AddReference("QuantConnect.Common")
AddReference("QuantConnect.Algorithm")
AddReference("QuantConnect.Algorithm.Framework")

from System import *
from QuantConnect import *
from QuantConnect.Data.UniverseSelection import *
from QuantConnect.Orders.Fees import ConstantFeeModel
from QuantConnect.Algorithm.Framework import QCAlgorithmFramework
from QuantConnect.Algorithm.Framework.Alphas import *
from QuantConnect.Algorithm.Framework.Portfolio import EqualWeightingPortfolioConstructionModel
from Selection.FundamentalUniverseSelectionModel import FundamentalUniverseSelectionModel

#
# Identify "pumped" penny stocks and predict that the price of a "Pumped" penny stock reverts to mean
#
# <br><br>This alpha is part of the Benchmark Alpha Series created by QuantConnect which are open sourced so the community and client funds can see an example of an alpha. 
# You can read the source code for this alpha on Github in <a href="https://github.com/QuantConnect/Lean/blob/master/Algorithm.CSharp/PumpAndDumpAlpha.cs">C#</a>
# or <a href="https://github.com/QuantConnect/Lean/blob/master/Algorithm.Python/Alphas/PumpAndDumpAlpha.py">Python</a>.
#

class PumpAndDumpAlpha(QCAlgorithmFramework):
    ''' Alpha Streams: Benchmark Alpha: Identify "pumped" penny stocks and predict that the price of a "pumped" penny stock reverts to mean'''

    def Initialize(self):

        self.SetStartDate(2018, 1, 1)
        self.SetCash(100000)

        # Set zero transaction fees
        self.SetSecurityInitializer(lambda security: security.SetFeeModel(ConstantFeeModel(0)))

        # select stocks using PennyStockUniverseSelectionModel
        self.UniverseSettings.Resolution = Resolution.Daily
        self.SetUniverseSelection(PennyStockUniverseSelectionModel())

        # Use PumpAndDumpAlphaModel to establish insights
        self.SetAlpha(PumpAndDumpAlphaModel())

        # Equally weigh securities in portfolio, based on insights
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel())


class PumpAndDumpAlphaModel(AlphaModel):
    '''Uses ranking of intraday percentage difference between open price and close price to create magnitude and direction prediction for insights'''

    def __init__(self, *args, **kwargs): 
        lookback = kwargs['lookback'] if 'lookback' in kwargs else 1
        resolution = kwargs['resolution'] if 'resolution' in kwargs else Resolution.Daily
        self.predictionInterval = Time.Multiply(Extensions.ToTimeSpan(resolution), lookback)
        self.numberOfStocks = kwargs['numberOfStocks'] if 'numberOfStocks' in kwargs else 10

    def Update(self, algorithm, data):
        insights = []
        symbolsRet = dict()

        for security in algorithm.ActiveSecurities.Values:
            if security.HasData:
                open = security.Open
                if open != 0:
                    # Intraday price change for penny stocks
                    symbolsRet[security.Symbol] = security.Close / open - 1

        # Rank penny stocks on one day price change and retrieve list of ten "pumped" penny stocks
        pumpedStocks = dict(sorted(symbolsRet.items(),
                                   key = lambda kv: (-round(kv[1], 6), kv[0]))[0:self.numberOfStocks])

        # Emit "down" insight for "pumped" penny stocks
        for key,value in pumpedStocks.items():
            insights.append(Insight.Price(key, self.predictionInterval, InsightDirection.Down, value, None))

        return insights


class PennyStockUniverseSelectionModel(FundamentalUniverseSelectionModel):
    '''Defines a universe of penny stocks, as a universe selection model for the framework algorithm:
    The stocks must have fundamental data
    The stock must have positive previous-day close price
    The stock must have volume between $1000000 and $10000 on the previous trading day
    The stock must cost less than $5'''

    def __init__(self):
        super().__init__(False, None, None)

        # Number of stocks in Coarse Universe
        self.numberOfSymbolsCoarse = 500
        self.lastMonth = -1
        self.symbols = []

    def SelectCoarse(self, algorithm, coarse):

        month = algorithm.Time.month
        if month == self.lastMonth:
            return self.symbols
        self.lastMonth = month

        filtered = [x for x in coarse if x.HasFundamentalData
                                      and  1000000 > x.Volume > 10000
                                      and 5 > x.Price > 0]

        # sort the stocks by dollar volume and take the top 500
        top = sorted(filtered, key=lambda x: x.DollarVolume, reverse=True)[:self.numberOfSymbolsCoarse]

        self.symbols = [ i.Symbol for i in top ]

        return self.symbols