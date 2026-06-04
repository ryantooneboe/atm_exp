import pytest
from atm_simulator import ATM

@pytest.fixture
def clean_atm():
	"""
	FIXTURE SETUP: This runs before every individual test case.
	It ensures each test starts with a fresh, un-mutated ATM instance
	with a controlled initial state.
	"""
	# Assuming the ATM constructor takes an initial balance and a valid PIN
	return ATM(initial_balance_gbp=500, pin="1234")

def test_example_system_readiness(clean_atm):
	"""
	SAMPLE STRUCTURE ONLY: This test simply verifies that the testing 
	framework can communicate with the ATM class module. 
	This is a dummy test and does not satisfy a business requirement.
	"""
	assert clean_atm is not None
	clean_atm.authenticate("1234")
	assert clean_atm.get_balance() == 500
