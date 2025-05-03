/**
 * Simple logger interface for the application
 */
export const logger = {
    error: (message: string): void => {
        console.error(`[ERROR] ${message}`);
    },
    warn: (message: string): void => {
        console.warn(`[WARN] ${message}`);
    },
    info: (message: string): void => {
        console.info(`[INFO] ${message}`);
    },
    debug: (message: string): void => {
        console.debug(`[DEBUG] ${message}`);
    }
}; 