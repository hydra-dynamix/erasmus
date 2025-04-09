"""
Rule Applicator Module

This module provides functionality for applying rules to code and managing rule chains.
It works in conjunction with the RulesParser to validate code against defined rules.
"""

from typing import List, Dict, Optional
from erasmus.core.rules_parser import Rule, ValidationError

class RuleApplicationError(Exception):
    """Exception raised when rule application fails."""
    pass

class RuleChain:
    """
    Represents a chain of rules to be applied in sequence.
    
    A rule chain maintains an ordered list of rules that should be applied
    to code in the specified order, regardless of rule priorities.
    
    Attributes:
        rules (List[Rule]): Ordered list of rules in the chain
    """
    
    def __init__(self, rules: List[Rule] = None):
        """
        Initialize a rule chain.
        
        Args:
            rules (List[Rule], optional): Initial list of rules. Defaults to None.
        """
        self.rules = rules or []
    
    def add_rule(self, rule: Rule) -> None:
        """
        Add a rule to the chain.
        
        Args:
            rule (Rule): Rule to add to the chain
        """
        self.rules.append(rule)
    
    def remove_rule(self, rule_name: str) -> None:
        """
        Remove a rule from the chain by name.
        
        Args:
            rule_name (str): Name of the rule to remove
            
        Raises:
            RuleApplicationError: If the rule is not found in the chain
        """
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                self.rules.pop(i)
                return
        raise RuleApplicationError(f"Rule '{rule_name}' not found in chain")

class RuleApplicator:
    """
    Manages and applies rules to code.
    
    This class handles the creation of rule chains and the application
    of rules to code in a specified order.
    
    Attributes:
        rules (List[Rule]): Available rules for application
        _rule_map (Dict[str, Rule]): Mapping of rule names to Rule objects
    """
    
    def __init__(self, rules: List[Rule]):
        """
        Initialize the rule applicator.
        
        Args:
            rules (List[Rule]): List of available rules
        """
        # Sort rules by priority (higher numbers first)
        self.rules = sorted(rules, key=lambda x: -x.priority)
        self._rule_map = {rule.name: rule for rule in rules}
    
    def get_rule(self, rule_name: str) -> Rule:
        """
        Get a rule by name.
        
        Args:
            rule_name (str): Name of the rule to retrieve
            
        Returns:
            Rule: The requested rule
            
        Raises:
            RuleApplicationError: If the rule is not found
        """
        rule = self._rule_map.get(rule_name)
        if not rule:
            raise RuleApplicationError(f"Rule '{rule_name}' not found")
        return rule
    
    def create_chain(self, rule_names: List[str]) -> RuleChain:
        """
        Create a new rule chain from a list of rule names.
        
        Args:
            rule_names (List[str]): Names of rules to include in the chain
            
        Returns:
            RuleChain: A new rule chain containing the specified rules
            
        Raises:
            RuleApplicationError: If any rule name is not found
        """
        chain = RuleChain()
        for name in rule_names:
            try:
                chain.add_rule(self.get_rule(name))
            except RuleApplicationError as e:
                raise RuleApplicationError(f"Failed to create chain: {str(e)}")
        return chain
    
    def apply_chain(self, chain: RuleChain, code: str) -> List[ValidationError]:
        """
        Apply a chain of rules to code.
        
        Rules are applied in the order specified by the chain, not by
        their individual priorities.
        
        Args:
            chain (RuleChain): Chain of rules to apply
            code (str): Code to validate
            
        Returns:
            List[ValidationError]: List of validation errors found
        """
        errors = []
        
        for rule in chain.rules:
            try:
                # Apply each rule individually and collect errors
                rule_errors = self._apply_rule(rule, code)
                errors.extend(rule_errors)
            except Exception as e:
                # If a rule fails to apply, add it as a validation error
                errors.append(ValidationError(
                    rule=rule,
                    message=f"Failed to apply rule: {str(e)}",
                    severity="error"
                ))
        
        return errors
    
    def _apply_rule(self, rule: Rule, code: str) -> List[ValidationError]:
        """
        Apply a single rule to code.
        
        Args:
            rule (Rule): Rule to apply
            code (str): Code to validate
            
        Returns:
            List[ValidationError]: List of validation errors found
        """
        import re
        errors = []
        
        try:
            pattern = re.compile(rule.pattern)
            matches = list(pattern.finditer(code))
            
            if rule.type.value == "code_style":
                # For code style rules, we want to ensure the pattern is NOT found
                # (except for require_* rules)
                if matches and not rule.name.startswith("require_"):
                    errors.append(ValidationError(
                        rule=rule,
                        message=f"Code violates rule: {rule.description}",
                        severity=rule.severity
                    ))
                # For require_* rules, we want to ensure the pattern IS found
                elif not matches and rule.name.startswith("require_"):
                    errors.append(ValidationError(
                        rule=rule,
                        message=f"Code does not match rule pattern: {rule.description}",
                        severity=rule.severity
                    ))
            elif rule.type.value == "documentation":
                # For documentation rules, we want to ensure the pattern IS found
                if not matches:
                    errors.append(ValidationError(
                        rule=rule,
                        message=f"Code does not match rule pattern: {rule.description}",
                        severity=rule.severity
                    ))
        except re.error as e:
            errors.append(ValidationError(
                rule=rule,
                message=f"Invalid rule pattern: {str(e)}",
                severity="error"
            ))
        
        return errors 