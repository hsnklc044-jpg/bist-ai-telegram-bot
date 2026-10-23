"""
QuantBIST Framework
Central Exception Definitions
"""

from __future__ import annotations

# =====================================================
# BASE
# =====================================================

class FrameworkError(Exception):
    """
    Base class for all framework exceptions.
    """


# =====================================================
# CONFIGURATION
# =====================================================

class ConfigurationError(FrameworkError):
    """
    Configuration related errors.
    """


# =====================================================
# INFRASTRUCTURE
# =====================================================

class InfrastructureError(FrameworkError):
    """
    Infrastructure related errors.
    """


class LoggerError(InfrastructureError):
    """
    Logger related errors.
    """


class CacheError(InfrastructureError):
    """
    Cache related errors.
    """


# =====================================================
# REPOSITORY
# =====================================================

class RepositoryError(FrameworkError):
    """
    Repository related errors.
    """


class PortfolioRepositoryError(RepositoryError):
    """
    Portfolio repository errors.
    """


# =====================================================
# PORTFOLIO
# =====================================================

class PortfolioError(FrameworkError):
    """
    Portfolio Engine errors.
    """


class PortfolioValidationError(PortfolioError):
    """
    Portfolio validation errors.
    """


class PortfolioOptimizationError(PortfolioError):
    """
    Portfolio optimization errors.
    """


# =====================================================
# MARKET
# =====================================================

class MarketError(FrameworkError):
    """
    Market Engine errors.
    """


class MarketScanError(MarketError):
    """
    Market scan errors.
    """


# =====================================================
# DECISION
# =====================================================

class DecisionError(FrameworkError):
    """
    Decision Engine errors.
    """


# =====================================================
# AI
# =====================================================

class RecommendationError(FrameworkError):
    """
    AI recommendation errors.
    """


class ScoringError(RecommendationError):
    """
    AI scoring errors.
    """


# =====================================================
# DASHBOARD
# =====================================================

class DashboardError(FrameworkError):
    """
    Dashboard errors.
    """


# =====================================================
# REPORTS
# =====================================================

class ReportError(FrameworkError):
    """
    Report generation errors.
    """


# =====================================================
# VALIDATION
# =====================================================

class ValidationError(FrameworkError):
    """
    Generic validation errors.
    """
