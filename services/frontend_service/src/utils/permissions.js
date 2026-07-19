export const ROLE_PERMISSIONS = {
  general_manager: ['view_overview', 'update_index', 'view_settings', 'manage_permissions', 'delete_session'],
  hr_admin: ['view_overview', 'update_index', 'view_settings', 'delete_session'],
  manager: ['view_overview'],
  employee: []
};

/**
 * Checks if the logged in user has the required permission.
 * @param {Object} user - The logged in user profile object
 * @param {string} requiredPermission - The permission name to check
 * @returns {boolean}
 */
export function hasPermission(user, requiredPermission) {
  if (!user || !user.roles) return false;
  
  return user.roles.some(role => {
    const permissions = ROLE_PERMISSIONS[role] || [];
    return permissions.includes(requiredPermission);
  });
}
