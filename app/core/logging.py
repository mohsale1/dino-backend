"""
Enhanced Production Logging Configuration
Comprehensive structured logging for debugging and monitoring
"""
import logging
import logging.config
import sys
import uuid
import time
import traceback
from typing import Dict, Any, Optional
import json
from datetime import datetime
from contextvars import ContextVar
from functools import wraps

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
operation_var: ContextVar[Optional[str]] = ContextVar('operation', default=None)


class EnhancedStructuredFormatter(logging.Formatter):
    """
    Enhanced formatter for structured logging with request correlation
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON with enhanced context"""
        
        # Get context variables
        request_id = request_id_var.get()
        user_id = user_id_var.get()
        operation = operation_var.get()
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "severity": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process
        }
        
        # Add context information
        if request_id:
            log_entry["request_id"] = request_id
        if user_id:
            log_entry["user_id"] = user_id
        if operation:
            log_entry["operation"] = operation
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 
                          'msecs', 'relativeCreated', 'thread', 'threadName', 
                          'processName', 'process', 'getMessage', 'exc_info', 
                          'exc_text', 'stack_info']:
                extra_fields[key] = value
        
        if extra_fields:
            log_entry["extra"] = extra_fields
        
        # Add performance metrics if available
        if hasattr(record, 'duration'):
            log_entry["performance"] = {
                "duration_ms": record.duration,
                "slow_query": record.duration > 1000 if hasattr(record, 'duration') else False
            }
        
        return json.dumps(log_entry, default=str)


class PerformanceFilter(logging.Filter):
    """Filter to add performance metrics to log records"""
    
    def filter(self, record):
        # Add timestamp for performance tracking
        if not hasattr(record, 'start_time'):
            record.start_time = time.time()
        return True


def setup_enhanced_logging(log_level: str = "INFO", enable_debug: bool = False) -> None:
    """
    Setup enhanced production logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_debug: Enable debug logging features
    """
    
    # Determine if we're in development mode
    is_development = log_level == "DEBUG" or enable_debug
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "enhanced_structured": {
                "()": EnhancedStructuredFormatter,
            },
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s"
            }
        },
        "filters": {
            "performance": {
                "()": PerformanceFilter,
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "enhanced_structured" if not is_development else "detailed",
                "stream": sys.stdout,
                "filters": ["performance"]
            },
            "error_console": {
                "class": "logging.StreamHandler",
                "level": "ERROR",
                "formatter": "enhanced_structured",
                "stream": sys.stderr,
                "filters": ["performance"]
            }
        },
        "root": {
            "level": log_level,
            "handlers": ["console", "error_console"] if not is_development else ["console"]
        },
        "loggers": {
            "app": {
                "level": log_level,
                "handlers": ["console"],
                "propagate": False
            },
            "app.database": {
                "level": "DEBUG" if is_development else "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "app.services": {
                "level": "DEBUG" if is_development else "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "app.api": {
                "level": "DEBUG" if is_development else "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "app.core": {
                "level": "DEBUG" if is_development else "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False
            },
            "uvicorn.access": {
                "level": "INFO" if is_development else "WARNING",
                "handlers": ["console"],
                "propagate": False
            },
            "google.cloud": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False
            },
            "google.auth": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False
            },
            "httpx": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False
            }
        }
    }
    
    logging.config.dictConfig(logging_config)
    
    # Log the logging configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Enhanced logging configured - Level: {log_level}, Debug: {enable_debug}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def set_request_context(request_id: str = None, user_id: str = None, operation: str = None):
    """
    Set request context for logging correlation
    
    Args:
        request_id: Unique request identifier
        user_id: User identifier
        operation: Operation being performed
    """
    if request_id:
        request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)
    if operation:
        operation_var.set(operation)


def clear_request_context():
    """Clear request context"""
    request_id_var.set(None)
    user_id_var.set(None)
    operation_var.set(None)


def generate_request_id() -> str:
    """Generate a unique request ID"""
    return str(uuid.uuid4())


class EnhancedLoggerMixin:
    """
    Enhanced mixin class to add comprehensive logging capabilities to any class
    """
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        return get_logger(self.__class__.__module__ + "." + self.__class__.__name__)
    
    def log_operation(self, operation: str, level: str = "INFO", **kwargs) -> None:
        """
        Log an operation with additional context
        
        Args:
            operation: Operation name
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            **kwargs: Additional context to log
        """
        extra = {"operation": operation}
        extra.update(kwargs)
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(log_level, f"Operation: {operation}", extra=extra)
    
    def log_error(self, error: Exception, operation: str = None, level: str = "ERROR", **kwargs) -> None:
        """
        Log an error with context
        
        Args:
            error: Exception that occurred
            operation: Operation that failed
            level: Log level
            **kwargs: Additional context
        """
        extra = {}
        if operation:
            extra["operation"] = operation
        extra.update(kwargs)
        
        # Add error details
        extra["error_type"] = type(error).__name__
        extra["error_message"] = str(error)
        
        log_level = getattr(logging, level.upper(), logging.ERROR)
        self.logger.log(
            log_level,
            f"Error in {operation or 'operation'}: {str(error)}", 
            exc_info=True, 
            extra=extra
        )
    
    def log_performance(self, operation: str, duration_ms: float, **kwargs) -> None:
        """
        Log performance metrics
        
        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            **kwargs: Additional context
        """
        extra = {
            "operation": operation,
            "duration": duration_ms,
            "performance_category": "slow" if duration_ms > 1000 else "normal"
        }
        extra.update(kwargs)
        
        level = logging.WARNING if duration_ms > 1000 else logging.INFO
        self.logger.log(
            level,
            f"Performance: {operation} took {duration_ms:.2f}ms",
            extra=extra
        )
    
    def log_debug(self, message: str, **kwargs) -> None:
        """Log debug message with context"""
        self.logger.debug(message, extra=kwargs)
    
    def log_info(self, message: str, **kwargs) -> None:
        """Log info message with context"""
        self.logger.info(message, extra=kwargs)
    
    def log_warning(self, message: str, **kwargs) -> None:
        """Log warning message with context"""
        self.logger.warning(message, extra=kwargs)
    
    def log_critical(self, message: str, **kwargs) -> None:
        """Log critical message with context"""
        self.logger.critical(message, extra=kwargs)


def log_function_call(include_args: bool = False, include_result: bool = False):
    """
    Decorator to log function calls with performance metrics
    
    Args:
        include_args: Whether to include function arguments in logs
        include_result: Whether to include function result in logs
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            
            # Log function entry
            log_data = {
                "function_name": func.__name__,
                "function_module": func.__module__,
                "operation": f"{func.__module__}.{func.__name__}"
            }
            
            if include_args:
                log_data["args"] = str(args)
                log_data["kwargs"] = str(kwargs)
            
            logger.debug(f"Entering function: {func.__name__}", extra=log_data)
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Log successful completion
                log_data["duration"] = duration_ms
                log_data["status"] = "success"
                
                if include_result:
                    log_data["result"] = str(result)[:500]  # Limit result size
                
                level = logging.WARNING if duration_ms > 1000 else logging.DEBUG
                logger.log(
                    level,
                    f"Function completed: {func.__name__} ({duration_ms:.2f}ms)",
                    extra=log_data
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # Log error
                log_data["duration"] = duration_ms
                log_data["status"] = "error"
                log_data["error_type"] = type(e).__name__
                log_data["error_message"] = str(e)
                
                logger.error(
                    f"Function failed: {func.__name__} ({duration_ms:.2f}ms) - {str(e)}",
                    exc_info=True,
                    extra=log_data
                )
                
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            
            # Log function entry
            log_data = {
                "function_name": func.__name__,
                "function_module": func.__module__,
                "operation": f"{func.__module__}.{func.__name__}"
            }
            
            if include_args:
                log_data["args"] = str(args)
                log_data["kwargs"] = str(kwargs)
            
            logger.debug(f"Entering function: {func.__name__}", extra=log_data)
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                
                # Log successful completion
                log_data["duration"] = duration_ms
                log_data["status"] = "success"
                
                if include_result:
                    log_data["result"] = str(result)[:500]  # Limit result size
                
                level = logging.WARNING if duration_ms > 1000 else logging.DEBUG
                logger.log(
                    level,
                    f"Function completed: {func.__name__} ({duration_ms:.2f}ms)",
                    extra=log_data
                )
                
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # Log error
                log_data["duration"] = duration_ms
                log_data["status"] = "error"
                log_data["error_type"] = type(e).__name__
                log_data["error_message"] = str(e)
                
                logger.error(
                    f"Function failed: {func.__name__} ({duration_ms:.2f}ms) - {str(e)}",
                    exc_info=True,
                    extra=log_data
                )
                
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Backward compatibility
LoggerMixin = EnhancedLoggerMixin
setup_logging = setup_enhanced_logging


# =============================================================================
# BUSINESS LOGGERS
# =============================================================================

class BusinessLogger:
    """Logger for business operations and events"""
    
    def __init__(self):
        self.logger = get_logger("business")
    
    def log_business_operation(self, 
                             operation: str,
                             entity_type: str,
                             entity_id: Optional[str] = None,
                             user_id: Optional[str] = None,
                             details: Optional[Dict[str, Any]] = None):
        """Log a business operation"""
        log_data = {
            "operation": operation,
            "entity_type": entity_type,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if entity_id:
            log_data["entity_id"] = entity_id
        
        if user_id:
            log_data["user_id"] = user_id
        
        if details:
            log_data["details"] = details
        
        self.logger.info(f"Business Operation: {operation}", extra=log_data)
    
    def log_user_action(self, 
                       user_id: str,
                       action: str,
                       resource: str,
                       resource_id: Optional[str] = None,
                       metadata: Optional[Dict[str, Any]] = None):
        """Log a user action"""
        log_data = {
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if resource_id:
            log_data["resource_id"] = resource_id
        
        if metadata:
            log_data["metadata"] = metadata
        
        self.logger.info(f"User Action: {action} on {resource}", extra=log_data)
    
    def log_security_event(self, 
                          event_type: str,
                          user_id: Optional[str] = None,
                          ip_address: Optional[str] = None,
                          details: Optional[Dict[str, Any]] = None):
        """Log a security event"""
        log_data = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if user_id:
            log_data["user_id"] = user_id
        
        if ip_address:
            log_data["ip_address"] = ip_address
        
        if details:
            log_data["details"] = details
        
        self.logger.warning(f"Security Event: {event_type}", extra=log_data)
    
    def log_error_event(self, 
                       error_type: str,
                       error_message: str,
                       user_id: Optional[str] = None,
                       context: Optional[Dict[str, Any]] = None):
        """Log an error event"""
        log_data = {
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if user_id:
            log_data["user_id"] = user_id
        
        if context:
            log_data["context"] = context
        
        self.logger.error(f"Error Event: {error_type}", extra=log_data)
    
    def log_performance_metric(self, 
                             operation: str,
                             duration_ms: float,
                             user_id: Optional[str] = None,
                             metadata: Optional[Dict[str, Any]] = None):
        """Log a performance metric"""
        log_data = {
            "operation": operation,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if user_id:
            log_data["user_id"] = user_id
        
        if metadata:
            log_data["metadata"] = metadata
        
        self.logger.info(f"Performance: {operation} took {duration_ms:.2f}ms", extra=log_data)


class APIRequestLogger:
    """Logger for API requests and responses"""
    
    def __init__(self):
        self.logger = get_logger("api")
    
    def log_request(self, 
                   method: str,
                   path: str,
                   user_id: Optional[str] = None,
                   ip_address: Optional[str] = None,
                   user_agent: Optional[str] = None):
        """Log an API request"""
        log_data = {
            "method": method,
            "path": path,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if user_id:
            log_data["user_id"] = user_id
        
        if ip_address:
            log_data["ip_address"] = ip_address
        
        if user_agent:
            log_data["user_agent"] = user_agent
        
        self.logger.info(f"API Request: {method} {path}", extra=log_data)
    
    def log_response(self, 
                    method: str,
                    path: str,
                    status_code: int,
                    duration_ms: float,
                    user_id: Optional[str] = None):
        """Log an API response"""
        log_data = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if user_id:
            log_data["user_id"] = user_id
        
        level = "info" if status_code < 400 else "warning" if status_code < 500 else "error"
        
        if level == "info":
            self.logger.info(f"API Response: {method} {path} - {status_code} ({duration_ms:.2f}ms)", extra=log_data)
        elif level == "warning":
            self.logger.warning(f"API Response: {method} {path} - {status_code} ({duration_ms:.2f}ms)", extra=log_data)
        else:
            self.logger.error(f"API Response: {method} {path} - {status_code} ({duration_ms:.2f}ms)", extra=log_data)


class AuditLogger:
    """Logger for audit trail events"""
    
    def __init__(self):
        self.logger = get_logger("audit")
    
    def log_data_change(self, 
                       entity_type: str,
                       entity_id: str,
                       operation: str,
                       user_id: str,
                       old_values: Optional[Dict[str, Any]] = None,
                       new_values: Optional[Dict[str, Any]] = None):
        """Log a data change event"""
        log_data = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "operation": operation,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if old_values:
            log_data["old_values"] = old_values
        
        if new_values:
            log_data["new_values"] = new_values
        
        self.logger.info(f"Data Change: {operation} {entity_type} {entity_id}", extra=log_data)
    
    def log_permission_change(self, 
                            user_id: str,
                            target_user_id: str,
                            permission_change: str,
                            admin_user_id: str):
        """Log a permission change event"""
        log_data = {
            "user_id": user_id,
            "target_user_id": target_user_id,
            "permission_change": permission_change,
            "admin_user_id": admin_user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        self.logger.info(f"Permission Change: {permission_change} for user {target_user_id}", extra=log_data)
    
    def log_access_attempt(self, 
                          user_id: str,
                          resource: str,
                          resource_id: str,
                          action: str,
                          allowed: bool,
                          reason: Optional[str] = None):
        """Log an access attempt"""
        log_data = {
            "user_id": user_id,
            "resource": resource,
            "resource_id": resource_id,
            "action": action,
            "allowed": allowed,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if reason:
            log_data["reason"] = reason
        
        level = "info" if allowed else "warning"
        message = f"Access {'Granted' if allowed else 'Denied'}: {action} on {resource} {resource_id}"
        
        if level == "info":
            self.logger.info(message, extra=log_data)
        else:
            self.logger.warning(message, extra=log_data)


class DatabaseLogger:
    """Logger for database operations"""
    
    def __init__(self):
        self.logger = get_logger("database")
    
    def log_query(self, 
                 operation: str,
                 collection: str,
                 duration_ms: float,
                 result_count: int = 0,
                 doc_id: Optional[str] = None):
        """Log a database query"""
        log_data = {
            "operation": operation,
            "collection": collection,
            "duration_ms": duration_ms,
            "result_count": result_count,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if doc_id:
            log_data["doc_id"] = doc_id
        
        self.logger.info(f"DB Query: {operation} on {collection} ({duration_ms:.2f}ms)", extra=log_data)
    
    def log_error(self, 
                 operation: str,
                 collection: str,
                 error: Exception,
                 doc_id: Optional[str] = None,
                 duration_ms: Optional[float] = None):
        """Log a database error"""
        log_data = {
            "operation": operation,
            "collection": collection,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if doc_id:
            log_data["doc_id"] = doc_id
        
        if duration_ms:
            log_data["duration_ms"] = duration_ms
        
        self.logger.error(f"DB Error: {operation} on {collection} - {error}", extra=log_data)


# Global logger instances
business_logger = BusinessLogger()
api_request_logger = APIRequestLogger()
audit_logger = AuditLogger()
db_logger = DatabaseLogger()


def get_business_logger() -> BusinessLogger:
    """Get business logger instance"""
    return business_logger


def get_api_request_logger() -> APIRequestLogger:
    """Get API request logger instance"""
    return api_request_logger


def get_audit_logger() -> AuditLogger:
    """Get audit logger instance"""
    return audit_logger


def get_db_logger() -> DatabaseLogger:
    """Get database logger instance"""
    return db_logger