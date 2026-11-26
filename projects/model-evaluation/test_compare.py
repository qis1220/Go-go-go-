import unittest
from compare import cost, run

class CostTests(unittest.TestCase):
    def setUp(self):
        self.rates={'input':2,'cached_input':0.2,'output':8}
    def test_cached_subset_not_double_counted(self):
        self.assertEqual(cost({'prompt_tokens':1000,'prompt_tokens_details':{'cached_tokens':400},'completion_tokens':100},self.rates),'0.00208')
    def test_missing_cache_is_zero(self):
        self.assertEqual(cost({'prompt_tokens':1000,'completion_tokens':100},self.rates),'0.0028')
    def test_invalid_usage(self):
        for usage in [{'prompt_tokens':1,'prompt_tokens_details':{'cached_tokens':2},'completion_tokens':0},
                      {'prompt_tokens':-1,'completion_tokens':0},{'prompt_tokens':1.5,'completion_tokens':0}]:
            with self.assertRaises(ValueError):cost(usage,self.rates)
    def test_invalid_prices(self):
        for rate in ['NaN','Infinity',-1]:
            with self.assertRaises(ValueError):cost({'prompt_tokens':1,'completion_tokens':1},{**self.rates,'input':rate})
    def test_error_preserves_other_config_and_is_not_zero_cost(self):
        cfg={'name':'bad','model':'example-a','currency':'DEMO','price_source':'synthetic','rates':self.rates,'fixture_answer':'test','fixture_usage':{'completion_tokens':1}}
        good={**cfg,'name':'good','fixture_usage':{'prompt_tokens':1,'completion_tokens':1}}
        result=run([cfg,good])
        self.assertEqual(result[0]['status'],'error')
        self.assertIsNone(result[0]['estimated_token_cost'])
        self.assertEqual(result[1]['status'],'completed')
        self.assertIsNone(result[1]['latency_ms'])
        self.assertEqual(result[1]['quality_review'],'unreviewed')

if __name__=='__main__':unittest.main()
